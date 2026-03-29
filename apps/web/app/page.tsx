import type { ReactNode } from "react";

import { getDashboardData, getTmuxSessions } from "@/lib/api";
import { SourcePolicyBadge } from "@/app/components/SourcePolicyBadge";
import { TmuxSessions } from "@/app/components/TmuxSessions";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

export default async function HomePage() {
  const [data, tmuxData] = await Promise.all([getDashboardData(), getTmuxSessions()]);
  const { curriculum, progression } = data;
  const activeCourse = progression.learning_plan?.active_course ?? "shell";
  const officialReferences = [
    ...curriculum.reference_stack.official_documents,
    ...curriculum.reference_stack.official_document_mirrors
  ];

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">42-training / MVP</p>
          <h1>One learning system, three tracks, one disciplined AI policy.</h1>
          <p className="lead">
            This app prepares a self-paced learner for 42 Lausanne through Shell, C and Python + AI,
            while keeping the 42 philosophy intact: autonomy, projects, peer-style reasoning and no blind copying.
          </p>
          <div className="hero-grid">
            <div className="metric-card">
              <span>Campus</span>
              <strong>{curriculum.metadata.campus}</strong>
            </div>
            <div className="metric-card">
              <span>Active course</span>
              <strong>{activeCourse}</strong>
            </div>
            <div className="metric-card">
              <span>Reference posture</span>
              <strong>{curriculum.metadata.reference_posture ?? "official docs first"}</strong>
            </div>
            <div className="metric-card">
              <span>Next command</span>
              <strong>{progression.next_command ?? "n/a"}</strong>
            </div>
          </div>
        </div>
        <aside className="status-panel">
          <h2>Current session</h2>
          <p>{progression.progress?.current_exercise ?? "No active exercise"}</p>
          <p>{progression.progress?.current_step ?? "No current step"}</p>
          <div className="stack-list">
            {(progression.progress?.in_progress ?? []).map((item) => (
              <Pill key={item}>{item}</Pill>
            ))}
          </div>
          <h2>Agent sessions</h2>
          <TmuxSessions sessions={tmuxData.sessions} />
        </aside>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Tracks</p>
          <h2>Triple-track architecture</h2>
        </div>
        <div className="track-grid">
          {curriculum.tracks.map((track) => (
            <article key={track.id} className={`track-card ${track.id === activeCourse ? "active" : ""}`}>
              <div className="card-topline">
                <span>{track.id}</span>
                <span>{track.modules.length} modules</span>
              </div>
              <h3>{track.title}</h3>
              <p>{track.summary}</p>
              <p className="muted">{track.why_it_matters}</p>
              <div className="module-list">
                {track.modules.map((module) => (
                  <div key={module.id} className="module-item">
                    <div className="module-header">
                      <strong>{module.title}</strong>
                      <Pill>{module.phase}</Pill>
                    </div>
                    <p>{module.deliverable}</p>
                    <div className="stack-list">
                      {module.skills.map((skill) => (
                        <Pill key={skill}>{skill}</Pill>
                      ))}
                    </div>
                    {module.reference_note ? <p className="module-note">{module.reference_note}</p> : null}
                    {(module.subject_refs ?? []).length > 0 ? (
                      <div className="module-reference-list">
                        {(module.subject_refs ?? []).map((reference) => (
                          <a
                            key={`${module.id}-${reference.label}`}
                            className="module-reference-item"
                            href={reference.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <div className="reference-topline">
                              <strong>{reference.document_title}</strong>
                              <span>{reference.coverage}</span>
                            </div>
                            <p>{reference.label}</p>
                            <p className="muted">
                              {reference.confidence} / {reference.tier}
                            </p>
                            {reference.mirror_path ? <p className="muted">{reference.mirror_path}</p> : null}
                          </a>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section split">
        <article className="panel">
          <p className="eyebrow">Bridges</p>
          <h2>Preparation checkpoints</h2>
          <div className="bridge-list">
            {curriculum.bridges.map((bridge) => (
              <div key={bridge.id} className="bridge-item">
                <strong>{bridge.title}</strong>
                <div className="stack-list">
                  {bridge.recommended_modules.map((item) => (
                    <Pill key={item}>{item}</Pill>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <p className="eyebrow">RAG Guardrails</p>
          <h2>Source policy</h2>
          <div className="policy-list">
            {curriculum.source_policy.tiers.map((tier) => (
              <div key={tier.id} className="policy-item">
                <strong>{tier.label}</strong>
                <SourcePolicyBadge tier={tier.id} />
              </div>
            ))}
          </div>
          <div className="confidence-list">
            {(curriculum.source_policy.confidence_model ?? []).map((item) => (
              <div key={item.level} className="confidence-item">
                <strong>{item.level}</strong>
                <p>{item.meaning}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="section split">
        <article className="panel">
          <p className="eyebrow">Reference Stack</p>
          <h2>Official documents and mirrors</h2>
          <div className="reference-list">
            {officialReferences.map((reference) => (
              <a key={reference.label} className="reference-item" href={reference.url} target="_blank" rel="noreferrer">
                <div className="reference-topline">
                  <strong>{reference.label}</strong>
                  <span>{reference.confidence ?? reference.tier}</span>
                </div>
                {reference.usage ? <p>{reference.usage}</p> : null}
                {reference.note ? <p className="muted">{reference.note}</p> : null}
              </a>
            ))}
          </div>
        </article>
        <article className="panel">
          <p className="eyebrow">Quality Toolchain</p>
          <h2>Available verification layers</h2>
          <div className="tool-list">
            {curriculum.reference_stack.quality_stack.map((tool) => (
              <a key={tool.id} className="tool-item tool-link" href={tool.url} target="_blank" rel="noreferrer">
                <div className="reference-topline">
                  <strong>{tool.label}</strong>
                  <span>{tool.language}</span>
                </div>
                <p>{tool.role}</p>
                <p className="muted">
                  {tool.authority} / {tool.kind}
                </p>
                {tool.note ? <p className="muted">{tool.note}</p> : null}
              </a>
            ))}
          </div>
        </article>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Quality Model</p>
          <h2>Equivalent rigor by language</h2>
        </div>
        <div className="quality-grid">
          {curriculum.reference_stack.quality_equivalents.map((item) => (
            <article key={item.language} className="quality-card">
              <div className="card-topline">
                <span>{item.language}</span>
                <span>quality contract</span>
              </div>
              <h3>{item.positioning}</h3>
              <p>{item.quality_contract}</p>
              <div className="quality-subsection">
                <strong>Automated gates</strong>
                <div className="stack-list">
                  {item.automated_gates.map((gate) => (
                    <Pill key={gate}>{gate}</Pill>
                  ))}
                </div>
              </div>
              <div className="quality-subsection">
                <strong>Human review focus</strong>
                <div className="stack-list">
                  {item.human_review_focus.map((focus) => (
                    <Pill key={focus}>{focus}</Pill>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Curriculum Mapping</p>
          <h2>Legacy backbone, emerging Python lane</h2>
        </div>
        <article className="panel">
          <p>{curriculum.curriculum_mapping.new_common_core_interpretation.summary}</p>
          <p className="muted">
            Confidence: {curriculum.curriculum_mapping.new_common_core_interpretation.confidence}.{" "}
            {curriculum.curriculum_mapping.new_common_core_interpretation.note}
          </p>
          <div className="milestone-grid">
            {(curriculum.curriculum_mapping.new_common_core_interpretation.milestones ?? []).map((item) => (
              <div key={item.milestone} className="milestone-card">
                <div className="reference-topline">
                  <strong>{item.milestone}</strong>
                  <span>{item.confidence}</span>
                </div>
                <div className="stack-list">
                  {item.projects.map((project) => (
                    <Pill key={project}>{project}</Pill>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="quality-subsection">
            <strong>Preserved legacy dimensions</strong>
            <div className="stack-list">
              {(curriculum.curriculum_mapping.legacy_common_core.preserved_dimensions ?? []).map((item) => (
                <Pill key={item}>{item}</Pill>
              ))}
            </div>
          </div>
          <div className="quality-subsection">
            <strong>Synthesis</strong>
            <div className="stack-list">
              {(curriculum.curriculum_mapping.synthesis?.principles ?? []).map((item) => (
                <Pill key={item}>{item}</Pill>
              ))}
            </div>
          </div>
        </article>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Predictions</p>
          <h2>Imagined subjects for the new Python and AI lane</h2>
        </div>
        <article className="panel">
          <div className="analogy-list">
            {(curriculum.curriculum_mapping.new_common_core_interpretation.style_analogies ?? []).map((item) => (
              <div key={`${item.legacy_anchor}-${item.new_project}`} className="analogy-item">
                <div className="reference-topline">
                  <strong>{item.new_project}</strong>
                  <span>{item.legacy_anchor}</span>
                </div>
                <p>{item.rationale}</p>
              </div>
            ))}
          </div>
          <div className="prediction-grid">
            {(curriculum.curriculum_mapping.new_common_core_interpretation.predicted_project_models ?? []).map((item) => (
              <article key={item.id} className="prediction-card">
                <div className="reference-topline">
                  <strong>{item.title}</strong>
                  <span>
                    {item.milestone} / {item.confidence}
                  </span>
                </div>
                <p>{item.predicted_subject_style}</p>
                <div className="quality-subsection">
                  <strong>Legacy style anchors</strong>
                  <div className="stack-list">
                    {item.legacy_style_anchors.map((anchor) => (
                      <Pill key={anchor}>{anchor}</Pill>
                    ))}
                  </div>
                </div>
                <div className="quality-subsection">
                  <strong>Likely constraints</strong>
                  <div className="stack-list">
                    {item.predicted_constraints.map((constraint) => (
                      <Pill key={constraint}>{constraint}</Pill>
                    ))}
                  </div>
                </div>
                <div className="quality-subsection">
                  <strong>Likely deliverables</strong>
                  <div className="stack-list">
                    {item.predicted_deliverables.map((deliverable) => (
                      <Pill key={deliverable}>{deliverable}</Pill>
                    ))}
                  </div>
                </div>
                <div className="quality-subsection">
                  <strong>Target skills</strong>
                  <div className="stack-list">
                    {item.predicted_core_skills.map((skill) => (
                      <Pill key={skill}>{skill}</Pill>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
