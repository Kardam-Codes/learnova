/*
 * File: LessonContentEditorPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor content editor for video, document, and image lessons.
 * What it is: A route-level editor page connected to the live admin content CRUD APIs.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { getContentEditorMock } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import {
  createAdminCourseContentRequest,
  deleteAdminContentRequest,
  fetchAdminContentRequest,
  updateAdminContentRequest,
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

function VideoContentFields({ content, updateField }) {
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
        <label className="editor-line-field">
          <span>Responsible :</span>
          <input
            type="text"
            value={content.responsible}
            onChange={(event) => updateField("responsible", event.target.value)}
          />
        </label>

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

function FileBasedContentFields({ content, label, updateField }) {
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

        <button type="button" className="catalog-action-button instructor-cta-button content-upload-button">
          Paste URL
        </button>
      </div>

      <div className="content-variant-footer-grid">
        <label className="editor-line-field">
          <span>Responsible :</span>
          <input
            type="text"
            value={content.responsible}
            onChange={(event) => updateField("responsible", event.target.value)}
          />
        </label>

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

function ContentVariantFields({ content, updateField }) {
  if (content.type === "Video") {
    return <VideoContentFields content={content} updateField={updateField} />;
  }

  if (content.type === "Document") {
    return (
      <FileBasedContentFields
        content={content}
        label="Document file:"
        updateField={updateField}
      />
    );
  }

  return (
    <FileBasedContentFields
      content={content}
      label="Image file :"
      updateField={updateField}
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

function AdditionalAttachmentTab({ content, updateField }) {
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

        <button type="button" className="catalog-action-button instructor-cta-button attachment-upload-button">
          Upload your file
        </button>
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

export default function LessonContentEditorPage() {
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
  const [statusMessage, setStatusMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const isNewContent = contentId === "new-content";

  useEffect(() => {
    let isMounted = true;

    const loadContent = async () => {
      if (isNewContent) {
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
        return;
      }

      try {
        const response = await fetchAdminContentRequest(contentId, token);
        if (isMounted) {
          setContent(buildEditorState(response));
        }
      } catch (error) {
        if (isMounted) {
          setContent({
            ...fallbackContent,
            duration: fallbackContent.duration ?? "",
          });
          setStatusMessage(error.message);
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

    try {
      await deleteAdminContentRequest(contentId, token);
      navigate(`/instructor/courses/${courseSlug}/edit`);
    } catch (error) {
      setStatusMessage(error.message);
    }
  };

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

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
              onClick={handleDelete}
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

          {statusMessage ? <p className="content-empty">{statusMessage}</p> : null}

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
                <ContentVariantFields content={content} updateField={updateField} />
              </section>
            ) : null}
            {activeTab === "Description" ? (
              <DescriptionTab content={content} updateField={updateField} />
            ) : null}
            {activeTab === "Additional attachment" ? (
              <AdditionalAttachmentTab content={content} updateField={updateField} />
            ) : null}
          </section>
        </section>
      </div>
    </main>
  );
}
