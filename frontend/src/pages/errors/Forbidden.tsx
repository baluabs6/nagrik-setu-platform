import ErrorLayout from "./ErrorLayout";

export default function Forbidden() {
  return (
    <ErrorLayout
      code="403"
      heading="You don't have access to this"
      message="Either you're not signed in, or your account doesn't have permission for this page. If you think that's wrong, contact your ward administrator or support."
    />
  );
}
