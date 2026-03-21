/*
 * File: LessonContentEditorPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor content editor for video, document, and image lessons.
 * What it is: A route-level editor page that matches the shared content, description, and attachment layout.
 */
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { getContentEditorMock } from "../data/instructorMock";

const editorTabs = ["Content", "Description", "Additional attachment"];
const categoryOptions = ["Video", "Document", "Image"];

function ContentVariantFields({ content }) {
  return (
    <>
      <div className="content-category-row">
        <span>Content Category :</span>
        {categoryOptions.map((option) => (
          <label key={option} className="category-choice">
            <input
              type="radio"
              name="contentType"
              defaultChecked={content.type === option}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>

      {content.type === "Video" ? (
        <>
          <label className="instructor-field">
            <span>Video Link:</span>
            <input type="text" defaultValue={content.videoLink} />
          </label>

          <label className="instructor-field instructor-field-short">
            <span>Responsible :</span>
            <input type="text" defaultValue={content.responsible} />
          </label>

          <label className="instructor-field instructor-field-short">
            <span>Duration :</span>
            <input type="text" defaultValue={content.duration} />
          </label>
        </>
      ) : null}

      {content.type === "Document" ? (
        <>
          <div className="upload-row">
            <label className="instructor-field instructor-field-short">
              <span>Document file:</span>
              <input type="text" defaultValue="" />
            </label>

            <button type="button" className="catalog-action-button instructor-cta-button">
              {content.fileLabel}
            </button>
          </div>

          <div className="editor-inline-grid">
            <label className="instructor-field instructor-field-short">
              <span>Responsible :</span>
              <input type="text" defaultValue={content.responsible} />
            </label>

            <label className="toggle-field">
              <span>Allow Download :</span>
              <input type="checkbox" defaultChecked={content.allowDownload} />
            </label>
          </div>
        </>
      ) : null}

      {content.type === "Image" ? (
        <>
          <div className="upload-row">
            <label className="instructor-field instructor-field-short">
              <span>Image file :</span>
              <input type="text" defaultValue="" />
            </label>

            <button type="button" className="catalog-action-button instructor-cta-button">
              {content.fileLabel}
            </button>
          </div>

          <div className="editor-inline-grid">
            <label className="instructor-field instructor-field-short">
              <span>Responsible :</span>
              <input type="text" defaultValue={content.responsible} />
            </label>

            <label className="toggle-field">
              <span>Allow Download :</span>
              <input type="checkbox" defaultChecked={content.allowDownload} />
            </label>
          </div>
        </>
      ) : null}
    </>
  );
}

function DescriptionTab({ content }) {
  return (
    <section className="editor-description-shell">
      {/* This textarea keeps the page editable while visually matching the large empty writing area from the mockup. */}
      <textarea
        className="editor-description-textarea"
        defaultValue={content.description}
        aria-label="Content description"
      />
    </section>
  );
}

function AdditionalAttachmentTab({ content }) {
  return (
    <section className="attachment-panel attachment-panel-compact">
      <div className="attachment-form-row">
        <label className="instructor-field instructor-field-short attachment-field">
          <span>File :</span>
          <input type="text" defaultValue={content.attachmentFile} />
        </label>

        <button type="button" className="catalog-action-button instructor-cta-button attachment-upload-button">
          Upload your file
        </button>
      </div>

      <label className="instructor-field instructor-field-short attachment-field">
        <span>Link :</span>
        <input type="text" defaultValue={content.attachmentLink} />
      </label>
    </section>
  );
}

export default function LessonContentEditorPage() {
  const { contentId = "video-advanced-sales" } = useParams();
  const content = useMemo(() => getContentEditorMock(contentId), [contentId]);
  const [activeTab, setActiveTab] = useState("Content");

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="content-editor-shell">
          <header className="content-editor-header">
            <span className="content-editor-label">Content title</span>
            <h1>{content.title}</h1>
          </header>

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
            {activeTab === "Content" ? <ContentVariantFields content={content} /> : null}
            {activeTab === "Description" ? <DescriptionTab content={content} /> : null}
            {activeTab === "Additional attachment" ? (
              <AdditionalAttachmentTab content={content} />
            ) : null}
          </section>
        </section>
      </div>
    </main>
  );
}
