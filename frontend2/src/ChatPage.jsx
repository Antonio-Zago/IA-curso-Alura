import { uuid } from "./utils/uuid";
import { useAppState } from "./StateContext";
import AppLayout from "./Layout";
import ChatBox from "./components/ChatBox";
import PromptSuggestions from "./components/PromptSuggestions";

// Endereço do supervisor (AG-UI). Pode ser definido em REACT_APP_AGENT_URL;
// por padrão usa o mesmo host de onde a página foi aberta, na porta 8080.
// Assim funciona tanto em http://localhost:3000 quanto em http://192.168.x.x:3000.
const AGENT_URL =
    process.env.REACT_APP_AGENT_URL ||
    `${window.location.protocol}//${window.location.hostname}:8080/`;

export default function ChatPage() {
    const { messages, setMessages, loading, setLoading, updateState } =
        useAppState();

    async function sendMessage(message) {
        if (!message.trim() || loading) return;

        const userMessage = { id: uuid(), role: "user", content: message };
        const assistantId = uuid();
        let assistantMessage = "";

        const setAssistantContent = (content) =>
            setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, content } : m)),
            );

        setMessages((prev) => [
            ...prev,
            userMessage,
            { id: assistantId, role: "assistant", content: "" },
        ]);
        setLoading(true);

        const payload = {
            thread_id: "1",
            run_id: uuid(),
            messages: [
                {
                    id: uuid(),
                    role: "user",
                    content: message,
                    user: { id: "user-123" },
                },
            ],
            state: {},
            tools: [],
            context: [],
            forwardedProps: {},
        };

        function handleEvent(event) {
            switch (event.type) {
                case "TEXT_MESSAGE_CONTENT":
                    assistantMessage += event.delta;
                    setAssistantContent(assistantMessage);
                    break;
                case "STATE_UPDATE":
                    updateState(event.state);
                    break;
                case "RUN_ERROR":
                    throw new Error(event.message || "Erro no agente");
                default:
                    break;
            }
        }

        try {
            const response = await fetch(AGENT_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "text/event-stream",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`HTTP ${response.status}: ${text.slice(0, 300)}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            // Um evento SSE pode chegar quebrado entre dois chunks, então
            // acumulamos no buffer e só processamos eventos completos ("\n\n").
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                buffer = parts.pop();

                for (const part of parts) {
                    for (const line of part.split("\n")) {
                        if (!line.startsWith("data:")) continue;
                        const jsonStr = line.slice(5).trim();
                        if (!jsonStr) continue;

                        let event;
                        try {
                            event = JSON.parse(jsonStr);
                        } catch (err) {
                            console.error("Evento inválido:", jsonStr, err);
                            continue;
                        }
                        handleEvent(event);
                    }
                }
            }
        } catch (err) {
            console.error("Erro ao chamar o agente:", err);
            setAssistantContent(
                `${assistantMessage}\n\n⚠️ **Erro ao falar com o agente** (${AGENT_URL}): ${err.message}`,
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <AppLayout>
            {messages.length === 0 ? (
                <PromptSuggestions onSelect={sendMessage} />
            ) : (
                <ChatBox
                    messages={messages}
                    setMessages={setMessages}
                    onSend={sendMessage}
                    loading={loading}
                />
            )}
        </AppLayout>
    );
}
