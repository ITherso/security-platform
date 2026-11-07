import { createRoot } from 'react-dom/client';
import { App, consoleStore } from './App';
import './styles.css';
const root = document.getElementById('root');
if (!root) throw new Error('console_mount_unavailable');
createRoot(root).render(<App />);
void consoleStore.reload();
