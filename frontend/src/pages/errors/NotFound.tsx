import ErrorLayout from "./ErrorLayout";

export default function NotFound() {
  return (
    <ErrorLayout
      code="404"
      heading="This page has gone missing"
      message="The report, page, or link you followed doesn't exist — it may have been moved, resolved, or never existed. Check the URL, or head back and search again."
    />
  );
}
