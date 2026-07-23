import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./components";
import { AppRouter } from "./router";

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRouter />
      </ToastProvider>
    </AuthProvider>
  );
}
