/// <reference types="vite/client" />
import type { Temporal as TemporalNamespace } from 'temporal-polyfill';

declare global {
  // eslint-disable-next-line no-var
  var Temporal: typeof TemporalNamespace;
}
