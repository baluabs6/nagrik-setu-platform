import ErrorLayout from "./ErrorLayout";

export default function BadRequest() {
  return (
    <ErrorLayout
      code="400"
      heading="That request didn't quite make sense"
      message="Something in the request was malformed — often a stray character in a form field or an outdated link. Try again, and if it keeps happening, let us know what you were doing."
    />
  );
}
