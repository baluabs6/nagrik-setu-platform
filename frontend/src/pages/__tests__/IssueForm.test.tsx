import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import IssueForm from "../IssueForm";
import { api } from "../../api/client";

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return {
    ...actual,
    api: {
      ...actual.api,
      presignUpload: vi.fn(),
      uploadToS3: vi.fn(),
      createIssue: vi.fn(),
    },
  };
});

describe("IssueForm", () => {
  beforeEach(() => {
    vi.mocked(api.presignUpload).mockReset();
    vi.mocked(api.uploadToS3).mockReset();
    vi.mocked(api.createIssue).mockReset();
  });

  it("submits without a photo when none is attached", async () => {
    vi.mocked(api.createIssue).mockResolvedValueOnce({
      id: "1", tracking_id: "NS-100001", category: "roads", locality: "Test Locality",
      description: "desc", status: "submitted", votes: 1, attachment_url: null, thumbnail_url: null,
      created_at: "", updated_at: "",
    });
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(<IssueForm onCreated={onCreated} />);

    await user.selectOptions(screen.getByLabelText(/category/i), "roads");
    await user.type(screen.getByLabelText(/city \/ locality/i), "Test Locality");
    await user.type(screen.getByLabelText(/what's happening/i), "desc");
    await user.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => expect(api.createIssue).toHaveBeenCalled());
    expect(api.presignUpload).not.toHaveBeenCalled();
    expect(onCreated).toHaveBeenCalled();
    expect(await screen.findByText("NS-100001")).toBeInTheDocument();
  });

  it("presigns and uploads a photo before creating the issue", async () => {
    vi.mocked(api.presignUpload).mockResolvedValueOnce({
      upload_url: "https://s3.example/put", attachment_key: "issue-attachments/abc.jpeg", max_bytes: 8_000_000,
    });
    vi.mocked(api.uploadToS3).mockResolvedValueOnce(undefined);
    vi.mocked(api.createIssue).mockResolvedValueOnce({
      id: "2", tracking_id: "NS-100002", category: "water", locality: "Another Place",
      description: "no water", status: "submitted", votes: 1,
      attachment_url: "https://s3.example/get", thumbnail_url: "https://s3.example/get-thumb",
      created_at: "", updated_at: "",
    });

    const user = userEvent.setup();
    render(<IssueForm onCreated={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText(/category/i), "water");
    await user.type(screen.getByLabelText(/city \/ locality/i), "Another Place");
    await user.type(screen.getByLabelText(/what's happening/i), "no water");

    const file = new File(["fake-bytes"], "photo.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/photo/i), file);

    await user.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => expect(api.createIssue).toHaveBeenCalled());
    expect(api.presignUpload).toHaveBeenCalledWith("image/jpeg");
    expect(api.uploadToS3).toHaveBeenCalledWith("https://s3.example/put", file);
    expect(api.createIssue).toHaveBeenCalledWith(
      expect.objectContaining({ attachment_key: "issue-attachments/abc.jpeg" })
    );
  });

  it("rejects a photo over 8MB before ever calling the API", async () => {
    const user = userEvent.setup();
    render(<IssueForm onCreated={vi.fn()} />);

    const bigFile = new File([new Uint8Array(9 * 1024 * 1024)], "huge.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/photo/i), bigFile);

    expect(await screen.findByRole("alert")).toHaveTextContent(/over 8MB/i);
    expect(api.presignUpload).not.toHaveBeenCalled();
  });
});
