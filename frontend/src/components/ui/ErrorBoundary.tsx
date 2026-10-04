import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="m-6 rounded-lg border border-red-200 bg-red-50 p-5 text-red-800">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-5 w-5" />
            Dashboard section could not be loaded.
          </div>
          <p className="mt-2 text-sm">{this.state.message || "Please retry or contact the system administrator."}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
