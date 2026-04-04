"use strict";
/**
 * Auto-discovers and activates known LLM instrumentor packages.
 *
 * Tries to `require()` known OpenInference instrumentor packages
 * and activate them. Missing packages are silently skipped.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.activateInstrumentors = activateInstrumentors;
const KNOWN_INSTRUMENTORS = [
    ["@arizeai/openinference-instrumentation-openai", "OpenAIInstrumentor"],
    [
        "@arizeai/openinference-instrumentation-anthropic",
        "AnthropicInstrumentor",
    ],
    [
        "@arizeai/openinference-instrumentation-langchain",
        "LangChainInstrumentor",
    ],
    [
        "@opentelemetry/instrumentation-openai",
        "OpenAIInstrumentation",
    ],
];
/**
 * Try to instrument all known LLM providers.
 * @returns List of activated instrumentor class names.
 */
function activateInstrumentors() {
    const activated = [];
    for (const [modulePath, className] of KNOWN_INSTRUMENTORS) {
        try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const mod = require(modulePath);
            const Cls = mod[className];
            if (Cls) {
                new Cls().instrument();
                activated.push(className);
            }
        }
        catch {
            // Package not installed or failed to activate — skip silently
        }
    }
    if (activated.length === 0) {
        console.debug("pixie: No LLM instrumentors activated. Install provider packages " +
            "(e.g. @arizeai/openinference-instrumentation-openai) for auto-capture.");
    }
    return activated;
}
//# sourceMappingURL=instrumentors.js.map