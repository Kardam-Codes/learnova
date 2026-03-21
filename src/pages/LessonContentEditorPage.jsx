/*
 * File: LessonContentEditorPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor content editor for video, document, and image lessons.
 * What it is: A route-level editor page connected to the live admin content CRUD APIs.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import LoadingBlock from "../components/LoadingBlock";
import InstructorNavbar from "../components/InstructorNavbar";
import StatusBanner from "../components/StatusBanner";
import { getContentEditorMock } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import {
  createAdminCourseContentRequest,
  deleteAdminContentRequest,
  fetchAdminContentRequest,
  fetchAdminUsersRequest,
  updateAdminContentRequest,
  uploadAdminFileRequest,
} from "../utils/apiClient";

const editorTabs = ["Content", "Description", "Additional attachment"];
const categoryOptions = ["Video", "Document", "Image"];

function mapModeToLabel(mode) {
  if (mode === "document") {
    return "Document";
  }

  if (mode === "image") {
    return "Image";
  }

  return "Video";
}

function mapLabelToMode(label) {
  if (label === "Document") {
    return "document";
  }

  if (label === "Image") {
    return "image";
  }

  return "video";
}

function buildEditorState(content) {
  const fileAttachment = content.attachments?.find((item) => item.attachmentType === "file");
  const linkAttachment = content.attachments?.find((item) => item.attachmentType === "link");

  return {
    id: content.slug,
    title: content.title ?? "",
    type: mapModeToLabel(content.contentMode ?? "video"),
    videoLink: content.contentUrl ?? "",
    responsible: content.responsibleName ?? "",
    responsibleUserId: content.responsibleUserId ?? null,
    duration: content.durationLabel ?? "",
    allowDownload: Boolean(content.allowDownload),
    description: content.description ?? "",
    attachmentFile: fileAttachment?.url ?? "",
    attachmentLink: linkAttachment?.url ?? "",
  };
}

function ContentCategorySelector({ selectedType, onChange }) {
  return (
    <div className="content-category-row">
      <span>Content Category :</span>
      {categoryOptions.map((option) => (
        <label key={option} className="category-choice">
          <input
            type="radio"
            name="contentType"
            checked={selectedType === option}
            onChange={() => onChange(option)}
          />
          <span>{option}</span>
        </label>
      ))}
    </div>
  );
}

function ResponsibleField({ content, updateField, adminUsers }) {
  return (
    <label className="editor-line-field">
      <span>Responsible :</span>
      <select
        value={content.responsibleUserId ?? ""}
        onChange={(event) => updateField("responsibleUserId", event.target.value || null)}
      >
        <option value="">Unassigned</option>
        {adminUsers.map((user) => (
          <option key={user.id} value={user.id}>
            {user.name} ({user.role})
          </option>
        ))}
      </select>
    </label>
  );
}

function VideoContentFields({ content, updateField, adminUsers }) {
  return (
    <section className="content-variant-shell">
      <ContentCategorySelector
        selectedType={content.type}
        onChange={(value) => updateField("type", value)}
      />

      <label className="editor-line-field editor-line-field-wide">
        <span>Video Link:</span>
        <input
          type="text"
          value={content.videoLink}
          onChange={(event) => updateField("videoLink", event.target.value)}
        />
      </label>

      <div className="content-variant-footer-grid">
        <ResponsibleField content={content} updateField={updateField} adminUsers={adminUsers} />

        <label className="editor-line-field">
          <span>Duration :</span>
          <input
            type="text"
            value={content.duration}
            onChange={(event) => updateField("duration", event.target.value)}
          />
        </label>
      </div>
    </section>
  );
}

function FileBasedContentFields({
  content,
  label,
  updateField,
  adminUsers,
  onUploadAsset,
  isUploadingAsset,
}) {
  return (
    <section className="content-variant-shell">
      <ContentCategorySelector
        selectedType={content.type}
        onChange={(value) => updateField("type", value)}
      />

      <div className="upload-row content-upload-row">
        <label className="editor-line-field editor-line-field-upload">
          <span>{label}</span>
          <input
            type="text"
            value={content.videoLink}
            onChange={(event) => updateField("videoLink", event.target.value)}
          />
        </label>

        <label className="catalog-action-button instructor-cta-button content-upload-button">
          {isUploadingAsset ? "Uploading..." : "Upload File"}
          <input type="file" hidden onChange={onUploadAsset} disabled={isUploadingAsset} />
        </label>
      </div>

      <div className="content-variant-footer-grid">
        <ResponsibleField content={content} updateField={updateField} adminUsers={adminUsers} />

        <label className="toggle-field content-download-toggle">
          <span>Allow Download :</span>
          <input
            type="checkbox"
            checked={content.allowDownload}
            onChange={(event) => updateField("allowDownload", event.target.checked)}
          />
        </label>
      </div>
    </section>
  );
}

function ContentVariantFields({
  content,
  updateField,
  adminUsers,
  onUploadAsset,
  isUploadingAsset,
}) {
  if (content.type === "Video") {
    return (
      <VideoContentFields
        content={content}
        updateField={updateField}
        adminUsers={adminUsers}
      />
    );
  }

  if (content.type === "Document") {
    return (
      <FileBasedContentFields
        content={content}
        label="Document file:"
        updateField={updateField}
        adminUsers={adminUsers}
        onUploadAsset={onUploadAsset}
        isUploadingAsset={isUploadingAsset}
      />
    );
  }

  return (
      <FileBasedContentFields
      content={content}
      label="Image file :"
      updateField={updateField}
      adminUsers={adminUsers}
      onUploadAsset={onUploadAsset}
      isUploadingAsset={isUploadingAsset}
    />
  );
}

function DescriptionTab({ content, updateField }) {
  return (
    <section className="editor-description-shell">
      <textarea
        className="editor-description-textarea"
        value={content.description}
        onChange={(event) => updateField("description", event.target.value)}
        aria-label="Content description"
      />
    </section>
  );
}

function AdditionalAttachmentTab({ content, updateField, onUploadAttachment, isUploadingAttachment }) {
  return (
    <section className="attachment-panel attachment-panel-compact">
      <div className="attachment-form-row">
        <label className="instructor-field instructor-field-short attachment-field">
          <span>File :</span>
          <input
            type="text"
            value={content.attachmentFile}
            onChange={(event) => updateField("attachmentFile", event.target.value)}
          />
        </label>

        <label className="catalog-action-button instructor-cta-button attachment-upload-button">
          {isUploadingAttachment ? "Uploading..." : "Upload your file"}
          <input type="file" hidden onChange={onUploadAttachment} disabled={isUploadingAttachment} />
        </label>
      </div>

      <label className="instructor-field instructor-field-short attachment-field">
        <span>Link :</span>
        <input
          type="text"
          value={content.attachmentLink}
          onChange={(event) => updateField("attachmentLink", event.target.value)}
        />
      </label>
    </section>
  );
}

export default function LessonContentEditorPage({ theme, toggleTheme }) {
  const { contentId = "video-advanced-sales" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const courseSlug = searchParams.get("course") ?? "odoo-crm";
  const fallbackContent = useMemo(() => getContentEditorMock(contentId), [contentId]);
  const [content, setContent] = useState(() => ({
    ...fallbackContent,
    duration: fallbackContent.duration ?? "",
  }));
  const [activeTab, setActiveTab] = useState("Content");
  const [adminUsers, setAdminUsers] = useState([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAsset, setIsUploadingAsset] = useState(false);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const isNewContent = contentId === "new-content";

  useEffect(() => {
    let isMounted = true;

    const loadContent = async () => {
      setIsLoading(true);
      if (isNewContent) {
        try {
          const userResponse = await fetchAdminUsersRequest(token, ["super_admin", "admin", "instructor"]);
          if (isMounted) {
            setAdminUsers(userResponse.users);
          }
        } catch (error) {
          if (isMounted) {
            setStatusMessage(error.message);
          }
        }
        setContent({
          id: "new-content",
          title: "",
          type: "Video",
          videoLink: "",
          responsible: "",
          responsibleUserId: null,
          duration: "",
          allowDownload: false,
          description: "",
          attachmentFile: "",
          attachmentLink: "",
        });
        setIsLoading(false);
        return;
      }

      try {
        const [response, userResponse] = await Promise.all([
          fetchAdminContentRequest(contentId, token),
          fetchAdminUsersRequest(token, ["super_admin", "admin", "instructor"]),
        ]);
        if (isMounted) {
          setContent(buildEditorState(response));
          setAdminUsers(userResponse.users);
        }
      } catch (error) {
        if (isMounted) {
          setContent({
            ...fallbackContent,
            duration: fallbackContent.duration ?? "",
          });
          setStatusMessage(error.message);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadContent();
    }

    return () => {
      isMounted = false;
    };
  }, [contentId, fallbackContent, isNewContent, token]);

  const updateField = (fieldName, value) => {
    setContent((current) => ({
      ...current,
      [fieldName]: value,
    }));
  };

  const handleUpload = async (file, category, fieldName) => {
    if (!file) {
      return;
    }

    const setUploading = fieldName === "attachmentFile" ? setIsUploadingAttachment : setIsUploadingAsset;
    setUploading(true);
    setStatusMessage("");

    try {
      const response = await uploadAdminFileRequest(token, file, category);
      updateField(fieldName, response.url);
      setStatusMessage(`${file.name} uploaded successfully.`);
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setUploading(false);
    }
  };

  const buildPayload = () => {
    const attachments = [];
    if (content.attachmentFile.trim()) {
      attachments.push({
        label: "File attachment",
        url: content.attachmentFile.trim(),
        attachmentType: "file",
      });
    }
    if (content.attachmentLink.trim()) {
      attachments.push({
        label: "External link",
        url: content.attachmentLink.trim(),
        attachmentType: "link",
      });
    }

    return {
      title: content.title,
      contentType: "lesson",
      contentMode: mapLabelToMode(content.type),
      description: content.description,
      contentUrl: content.videoLink || null,
      allowDownload: content.allowDownload,
      durationLabel: content.duration || null,
      responsibleUserId: content.responsibleUserId,
      attachments,
    };
  };

  const handleSave = async () => {
    setIsSaving(true);
    setStatusMessage("");

    try {
      const response = isNewContent
        ? await createAdminCourseContentRequest(courseSlug, token, buildPayload())
        : await updateAdminContentRequest(contentId, token, buildPayload());

      setContent(buildEditorState(response));
      setStatusMessage("Content saved successfully.");

      if (isNewContent || response.slug !== contentId) {
        navigate(`/instructor/content/${response.slug}/edit?course=${response.courseSlug}`, {
          replace: true,
        });
      }
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (isNewContent) {
      navigate(`/instructor/courses/${courseSlug}/edit`);
      return;
    }

    setIsDeleting(true);
    try {
      await deleteAdminContentRequest(contentId, token);
      navigate(`/instructor/courses/${courseSlug}/edit`);
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar theme={theme} toggleTheme={toggleTheme} />

      <div className="course-page-card instructor-shell">
        <section className="content-editor-shell">
          <header className="content-editor-header">
            <span className="content-editor-label">Content title</span>
            <h1>{content.title || "New Content"}</h1>
          </header>

          <div className="inline-button-row instructor-top-right">
            <Link
              to={`/instructor/courses/${courseSlug}/edit`}
              className="catalog-action-button instructor-ghost-button"
            >
              Back to Course
            </Link>
            <button
              type="button"
              className="catalog-action-button instructor-ghost-button"
              onClick={() => setShowDeleteDialog(true)}
            >
              Delete
            </button>
            <button
              type="button"
              className="catalog-action-button instructor-cta-button"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? "Saving..." : "Save Content"}
            </button>
          </div>

          <StatusBanner
            tone={
              statusMessage?.toLowerCase().includes("successfully")
                ? "success"
                : statusMessage?.toLowerCase().includes("could not") ||
                    statusMessage?.toLowerCase().includes("failed")
                  ? "error"
                  : "info"
            }
            message={statusMessage}
            onClose={() => setStatusMessage("")}
          />

          {isLoading ? (
            <LoadingBlock
              title="Loading content editor"
              description="Preparing lesson settings, uploads, and responsible user choices."
            />
          ) : (
          <>
          <div className="instructor-tab-row" role="tablist" aria-label="Content editor tabs">
            {editorTabs.map((tab) => (
              <button
                key={tab}
                type="button"
                className={`course-tab${activeTab === tab ? " is-active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          <section className="instructor-panel content-editor-panel">
            {activeTab === "Content" ? (
              <section className="content-variant-shell">
                <label className="editor-line-field editor-line-field-wide">
                  <span>Content Title:</span>
                  <input
                    type="text"
                    value={content.title}
                    onChange={(event) => updateField("title", event.target.value)}
                  />
                </label>
                <ContentVariantFields
                  content={content}
                  updateField={updateField}
                  adminUsers={adminUsers}
                  onUploadAsset={(event) =>
                    handleUpload(event.target.files?.[0], "content-assets", "videoLink")
                  }
                  isUploadingAsset={isUploadingAsset}
                />
              </section>
            ) : null}
            {activeTab === "Description" ? (
              <DescriptionTab content={content} updateField={updateField} />
            ) : null}
            {activeTab === "Additional attachment" ? (
              <AdditionalAttachmentTab
                content={content}
                updateField={updateField}
                onUploadAttachment={(event) =>
                  handleUpload(event.target.files?.[0], "content-attachments", "attachmentFile")
                }
                isUploadingAttachment={isUploadingAttachment}
              />
            ) : null}
          </section>
          </>
          )}
        </section>
      </div>
      {showDeleteDialog ? (
        <ConfirmDialog
          title="Delete content"
          description="This content item will be removed from the course. This action cannot be undone."
          confirmLabel="Delete content"
          isSubmitting={isDeleting}
          onConfirm={handleDelete}
          onClose={() => setShowDeleteDialog(false)}
        />
      ) : null}
    </main>
  );
}
