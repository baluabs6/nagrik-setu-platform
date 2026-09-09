import { FormEvent, useState } from "react";
import { api, ApiError, Issue } from "../api/client";

const CATEGORIES: { value: string; label: string }[] = [
  { value: "roads", label: "Roads & Potholes" },
  { value: "water", label: "Water Supply" },
  { value: "garbage", label: "Garbage & Sanitation" },
  { value: "power", label: "Power Outages" },
  { value: "lighting", label: "Street Lighting" },
  { value: "transport", label: "Public Transport" },
  { value: "pollution", label: "Air & Noise Pollution" },
  { value: "grievance", label: "Corruption & Grievances" },
];

const MAX_PHOTO_BYTES = 8 * 1024 * 1024;

interface Props {
  onCreated: (issue: Issue) => void;
}

export default function IssueForm({ onCreated }: Props) {
  const [category, setCategory] = useState("");
  const [locality, setLocality] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trackingId, setTrackingId] = useState<string | null>(null);

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setError(null);
    if (file && file.size > MAX_PHOTO_BYTES) {
      setError("That photo is over 8MB — try a smaller one.");
      setPhoto(null);
      e.target.value = "";
      return;
    }
    setPhoto(file);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setTrackingId(null);
    setSubmitting(true);

    try {
      let attachmentKey: string | undefined;

      if (photo) {
        const presign = await api.presignUpload(photo.type);
        await api.uploadToS3(presign.upload_url, photo);
        attachmentKey = presign.attachment_key;
      }

      const issue = await api.createIssue({
        category,
        locality,
        description,
        ...(attachmentKey ? { attachment_key: attachmentKey } : {}),
      });

      setTrackingId(issue.tracking_id);
      onCreated(issue);
      setCategory("");
      setLocality("");
      setDescription("");
      setPhoto(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong filing that report. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 14, maxWidth: 480 }}>
      <div>
        <label htmlFor="category">Category</label>
        <select id="category" value={category} onChange={(e) => setCategory(e.target.value)} required>
          <option value="">Choose the issue type</option>
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="locality">City / locality</label>
        <input
          id="locality"
          value={locality}
          onChange={(e) => setLocality(e.target.value)}
          placeholder="e.g. Indiranagar, Bengaluru"
          required
        />
      </div>

      <div>
        <label htmlFor="description">What's happening</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the issue — where exactly, since when, who it affects"
          required
        />
      </div>

      <div>
        <label htmlFor="photo">Photo (optional, up to 8MB)</label>
        <input id="photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePhotoChange} />
      </div>

      {error && <p role="alert">{error}</p>}

      {trackingId && (
        <p role="status">
          Report filed. Tracking ID <strong>{trackingId}</strong>.
        </p>
      )}

      <button type="submit" disabled={submitting}>
        {submitting ? "Submitting…" : "Submit report"}
      </button>
    </form>
  );
}
