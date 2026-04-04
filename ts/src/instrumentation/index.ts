/**
 * Re-export public API from the instrumentation submodule.
 */

// Span types
export type {
  TextContent,
  ImageContent,
  MessageContent,
  ToolCall,
  ToolDefinition,
  SystemMessage,
  UserMessage,
  AssistantMessage,
  ToolResultMessage,
  Message,
  LLMSpan,
  ObserveSpan,
} from "./spans";

export {
  createTextContent,
  createImageContent,
  createSystemMessage,
  createUserMessage,
  createUserMessageFromText,
  createAssistantMessage,
  createToolResultMessage,
} from "./spans";

// Handler
export { InstrumentationHandler } from "./handler";

// Context
export { ObservationContext, NoOpObservationContext } from "./context";

// Observation API
export {
  init,
  addHandler,
  removeHandler,
  startObservation,
  startObservationSync,
  observe,
  flush,
} from "./observation";
export type { InitOptions, StartObservationOptions } from "./observation";

// Handlers
export { StorageHandler, enableStorage } from "./handlers";
export type { ObservationStore } from "./handlers";
