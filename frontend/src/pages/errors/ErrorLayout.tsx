import { ReactNode } from "react";
import { Link } from "react-router-dom";
import "../../styles/errors.css";

interface ErrorLayoutProps {
  code: string;
  accent?: "indigo" | "signal" | "turmeric";
  heading: string;
  message: string;
  children?: ReactNode;
}

export default function ErrorLayout({ code, accent = "indigo", heading, message, children }: ErrorLayoutProps) {
  const codeClass =
    accent === "signal"
      ? "error-page__code error-page__code--signal"
      : accent === "turmeric"
      ? "error-page__code error-page__code--turmeric"
      : "error-page__code";

  return (
    <div className="error-page">
      <div className="error-page__card">
        <div className="error-page__rule" />
        <div className={codeClass}>{code}</div>
        <h1 className="error-page__heading">{heading}</h1>
        <p className="error-page__message">{message}</p>
        <div className="error-page__actions">
          <Link className="error-page__btn error-page__btn--primary" to="/">
            Back to home
          </Link>
          <a className="error-page__btn error-page__btn--secondary" href="mailto:support@nagriksetu.in">
            Contact support
          </a>
        </div>
        {children}
      </div>
    </div>
  );
}
