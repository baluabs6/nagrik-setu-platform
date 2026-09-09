import { Component, ErrorInfo, ReactNode } from "react";
import ServerError from "./ServerError";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // In production this reports to Sentry/CloudWatch RUM instead of console.
    console.error("Uncaught render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <ServerError />;
    }
    return this.props.children;
  }
}
