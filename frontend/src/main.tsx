import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { initGlobalAriaValidation } from './lib/ariaValidation';
import { ensureTemporal } from './lib/temporal';
import './styles/base.css';
import './styles/components.css';

async function bootstrap() {
  await ensureTemporal();
  initGlobalAriaValidation();

  const rootEl = document.getElementById('root');
  if (!rootEl) return;

  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

void bootstrap();
