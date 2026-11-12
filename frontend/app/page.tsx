"use client";

import { FormEvent, useEffect, useState } from "react";

type Idea = {
  id: number;
  title: string;
  problem: string;
  category: string;
  target_users: string;
  core_features: string;
  suggested_stack: string;
  why_now: string;
  is_favorite: boolean;
  created_at: string;
  generation_source: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function IdeaCard({ idea, onFavorite }: { idea: Idea; onFavorite: (idea: Idea) => void }) {
  return (
    <article className="idea-card">
      <div className="card-head">
        <div><p className="eyebrow">{idea.category}{idea.generation_source === "fallback" ? " · offline idea" : ""}</p><h2>{idea.title}</h2></div>
        <button className="favorite" onClick={() => onFavorite(idea)} aria-label={`Favorite ${idea.title}`}>
          {idea.is_favorite ? "★" : "☆"}
        </button>
      </div>
      <p className="problem">{idea.problem}</p>
      <dl>
        <div><dt>For</dt><dd>{idea.target_users}</dd></div>
        <div><dt>Core features</dt><dd>{idea.core_features}</dd></div>
        <div><dt>Stack</dt><dd>{idea.suggested_stack}</dd></div>
        <div><dt>Why now</dt><dd>{idea.why_now}</dd></div>
      </dl>
    </article>
  );
}

export default function Home() {
  const [category, setCategory] = useState("");
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showFavorites, setShowFavorites] = useState(false);
  const [error, setError] = useState("");

  const loadIdeas = async (favoritesOnly = showFavorites) => {
    try {
      const response = await fetch(`${apiUrl}/ideas${favoritesOnly ? "?favorites_only=true" : ""}`);
      if (!response.ok) throw new Error("Could not load your idea history.");
      setIdeas(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the API.");
    }
  };

  useEffect(() => { void loadIdeas(false); }, []);

  const generate = async (event: FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/ideas/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: category || null }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Generation failed. Please try again.");
      setIdeas((current) => [payload, ...current]);
      setShowFavorites(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the API.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFavorite = async (idea: Idea) => {
    setError("");
    try {
      const response = await fetch(`${apiUrl}/ideas/${idea.id}/favorite`, { method: "PATCH" });
      if (!response.ok) throw new Error("Could not update favorite.");
      const update = await response.json();
      if (showFavorites && !update.is_favorite) setIdeas((current) => current.filter(({ id }) => id !== idea.id));
      else setIdeas((current) => current.map((item) => item.id === idea.id ? { ...item, ...update } : item));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the API.");
    }
  };

  const changeView = async (favorites: boolean) => {
    setShowFavorites(favorites);
    setError("");
    await loadIdeas(favorites);
  };

  return (
    <main>
      <section className="hero">
        <p className="brand">IDEALIST</p>
        <h1>Find your next practical idea.</h1>
        <p className="intro">A focused generator for software, automation, and digital business concepts that avoid repeating your past ideas.</p>
        <form onSubmit={generate}>
          <label htmlFor="category">Category <span>optional</span></label>
          <div className="generate-row">
            <input id="category" value={category} onChange={(event) => setCategory(event.target.value)} placeholder="e.g. car websites, POS, automation" maxLength={100} />
            <button type="submit" disabled={isLoading}>{isLoading ? "Thinking…" : "Generate idea"}</button>
          </div>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </section>
      <section className="ideas-section">
        <div className="toolbar"><h2>{showFavorites ? "Favorites" : "Your idea history"}</h2><button className="text-button" onClick={() => void changeView(!showFavorites)}>{showFavorites ? "View all" : "View favorites"}</button></div>
        {ideas.length ? <div className="idea-grid">{ideas.map((idea) => <IdeaCard key={idea.id} idea={idea} onFavorite={(item) => void toggleFavorite(item)} />)}</div> : <div className="empty"><p>{showFavorites ? "No favorites yet." : "Your generated ideas will appear here."}</p></div>}
      </section>
    </main>
  );
}
