import Link from "next/link";

export default function Home() {
  return (
    <main className="page">
      <section className="hero">
        <h1 className="title">ML-AUTOC Experiment Archive</h1>
        <p className="subtitle">
          Explore downloadable code and experiment materials from my paper.
        </p>

        <div className="buttonRow">
          <Link href="/downloads" className="navButton">
            Download Zip Files
          </Link>

          <Link href="/experiments" className="navButton secondaryButton">
            View Experiment Section
          </Link>
        </div>
      </section>
    </main>
  );
}