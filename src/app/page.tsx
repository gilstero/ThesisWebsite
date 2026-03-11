import Link from "next/link";

export default function Home() {
  return (
    <main className="page">
      <section className="hero">
        <h1 className="title">
          Multi-Level Area Under the Targeting Operating Characteristic Experiment Archive
        </h1>

        <h1 className="paperTitle">
          “Precedence-Aware Resource Allocation: Extending the AUTOC Framework to Multi-Level Treatments”
        </h1>

        <p className="subtitle">
          Explore downloadable code and experiment materials from my undergraduate thesis.
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