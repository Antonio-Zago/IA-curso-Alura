import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import AppLayout from "./Layout";
import { useAppState } from "./StateContext";

export default function StateUtilPage() {
    const { state } = useAppState();
    const responses = state.responses || [];

    // ------------------------------------
    // Funções para extrair dados
    // ------------------------------------
    const extractData = (text) => {
        if (typeof text !== "string") return null;
        const data = {};

        // Casa "Rótulo: valor", aceitando negrito em Markdown,
        // ex.: "**Nome completo:** João" ou "Nome completo - João"
        const field = (label, value) =>
            text.match(
                new RegExp(
                    String.raw`\**\s*${label}\s*\**\s*[:\-]\s*\**\s*${value}`,
                    "iu",
                ),
            );

        const nameMatch = field(String.raw`nome(?:\s+completo)?`, String.raw`([\p{L} ]+)`);
        if (nameMatch) data.Nome = nameMatch[1].trim();

        const cpfMatch = field("cpf", String.raw`([\d.\-]{11,14})`);
        if (cpfMatch) data.CPF = cpfMatch[1].trim();

        const accountMatch = field(String.raw`n[uú]mero(?:\s+da)?\s+conta`, String.raw`(\d+)`);
        if (accountMatch) data.Conta = accountMatch[1].trim();

        const saldoMatch = field("saldo", String.raw`R\$\s*([\d.,]+)`);
        if (saldoMatch)
            data.Saldo = `R$ ${parseFloat(
                saldoMatch[1].replace(/\./g, "").replace(",", "."),
            ).toFixed(2)}`;

        const cardNumberMatch = field(
            String.raw`n[uú]mero(?:\s+do)?\s+cart[aã]o`,
            String.raw`(\d[\d ]*\d)`,
        );
        if (cardNumberMatch) data.CartaoNumero = cardNumberMatch[1].trim();

        const cardTypeMatch = field("tipo", String.raw`([\p{L} ]+)`);
        if (cardTypeMatch) data.CartaoTipo = cardTypeMatch[1].trim();

        const cardLimitMatch = field(
            String.raw`limite(?:\s+dispon[ií]vel)?`,
            String.raw`R\$\s*([\d.,]+)`,
        );
        if (cardLimitMatch)
            data.CartaoLimite = `R$ ${cardLimitMatch[1].trim()}`;

        return Object.keys(data).length ? data : null;
    };

    // ------------------------------------
    // Preparar respostas filtradas
    // ------------------------------------
    const filteredResponses = [];
    for (const r of responses) {
        if (typeof r === "string") {
            filteredResponses.push({ message: r, data: extractData(r) });
        } else {
            for (const value of Object.values(r)) {
                if (value && value.trim()) {
                    filteredResponses.push({ message: value, data: extractData(value) });
                }
            }
        }
    }

    // ------------------------------------
    // Função para mascarar cartão
    // ------------------------------------
    const maskCardNumber = (number) => {
        if (!number) return "**** **** **** ****";
        const clean = number.replace(/\D/g, "");
        if (clean.length <= 8) return clean.slice(0, 4) + " **** ****";
        return `${clean.slice(0, 4)} **** **** ${clean.slice(-2)}`;
    };

    // ------------------------------------
    // Motion Variants
    // ------------------------------------
    const cardVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 },
    };

    return (
        <AppLayout>
            <div className="p-6 flex-1 overflow-auto flex flex-col bg-gray-900">
                <h1 className="text-3xl font-bold mb-6 text-white">
                    Histórico de Respostas
                </h1>
                {filteredResponses.length === 0 ? (
                    <p className="text-gray-400 text-lg">
                        Nenhuma resposta registrada ainda.
                    </p>
                ) : (
                    <div className="flex flex-col gap-4">
                        <AnimatePresence>
                            {filteredResponses.map(({ message, data }, i) => {
                                const isCard = data && data.CartaoNumero && data.CartaoTipo;
                                return (
                                    <motion.div
                                        key={i}
                                        initial="hidden"
                                        animate="visible"
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        variants={cardVariants}
                                        transition={{ duration: 0.3, ease: "easeOut" }}
                                        className="p-4 rounded-2xl shadow-lg max-w-xl w-full"
                                    >
                                        {data ? (
                                            isCard ? (
                                                <div
                                                    className={`self-end bg-gradient-to-r from-blue-600 to-blue-400 p-6 rounded-xl shadow-lg text-white w-full max-w-sm font-mono`}
                                                >
                                                    <div className="flex justify-between items-center mb-4">
                                                        <span className="text-lg font-semibold">
                                                            {data.CartaoTipo}
                                                        </span>
                                                        <span className="text-sm">MDBank</span>
                                                    </div>
                                                    <div className="text-2xl tracking-widest mb-4">
                                                        {maskCardNumber(data.CartaoNumero)}
                                                    </div>
                                                    <div className="flex justify-between text-sm">
                                                        <span>{data.Nome}</span>
                                                        <span>{data.CartaoLimite}</span>
                                                    </div>
                                                </div>
                                            ) : (
                                                Object.entries(data).map(([key, value]) => (
                                                    <span key={key}>
                                                        <span className="bg-gray-800 px-3 py-1 rounded-full text-sm text-white">
                                                            {key}: {value}
                                                        </span>
                                                    </span>
                                                ))
                                            )
                                        ) : (
                                            <div className="bg-green-700 self-end">
                                                <ReactMarkdown className="prose prose-invert">
                                                    {message}
                                                </ReactMarkdown>
                                            </div>
                                        )}
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </div>
                )}
            </div>
        </AppLayout>
    );
}