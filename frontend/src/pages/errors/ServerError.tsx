import ErrorLayout from "./ErrorLayout";

export default function ServerError() {
  return (
    <ErrorLayout
      code="500"
      accent="signal"
      heading="Something went wrong on our end"
      message="Not you — us. Our team has already been notified. Try refreshing in a minute; if it keeps happening, the support contact below can help."
    />
  );
}
