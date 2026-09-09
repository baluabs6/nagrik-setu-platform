import ErrorLayout from "./ErrorLayout";

export default function ServiceUnavailable() {
  return (
    <ErrorLayout
      code="503"
      accent="turmeric"
      heading="We'll be right back"
      message="The service is temporarily unavailable — either scheduled maintenance or a failover to our disaster-recovery region is in progress. This usually resolves within a few minutes."
    />
  );
}
