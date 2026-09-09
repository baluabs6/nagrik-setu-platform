import { Link } from "react-router-dom";
import ErrorLayout from "./ErrorLayout";

export default function Unauthorized() {
  return (
    <ErrorLayout
      code="401"
      heading="Sign in to continue"
      message="This page needs you to be signed in. Log in with your account and you'll be brought right back here."
    >
      <div style={{ marginTop: 8 }}>
        <Link className="error-page__btn error-page__btn--primary" to="/login">
          Sign in
        </Link>
      </div>
    </ErrorLayout>
  );
}
