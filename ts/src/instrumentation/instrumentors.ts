/**
 * Auto-discovers and activates known LLM instrumentor packages.
 *
 * Tries to `require()` known OpenInference instrumentor packages
 * and activate them. Missing packages are silently skipped.
 */

const KNOWN_INSTRUMENTORS: Array<[string, string]> = [
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
export function activateInstrumentors(): string[] {
  const activated: string[] = [];

  for (const [modulePath, className] of KNOWN_INSTRUMENTORS) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const mod = require(modulePath) as Record<string, unknown>;
      const Cls = mod[className] as { new (): { instrument(): void } } | undefined;
      if (Cls) {
        new Cls().instrument();
        activated.push(className);
      }
    } catch {
      // Package not installed or failed to activate — skip silently
    }
  }

  if (activated.length === 0) {
    console.debug(
      "pixie: No LLM instrumentors activated. Install provider packages " +
        "(e.g. @arizeai/openinference-instrumentation-openai) for auto-capture."
    );
  }

  return activated;
}
