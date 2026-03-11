export default function DownloadsPage() {
    return (
      <main className="page">
        <section className="contentSection">
          <h1 className="sectionTitle">Download Files</h1>
          <p className="sectionIntro">
            Download the source materials used to develop and run the experiments
            from my paper.
          </p>
  
          <div className="downloadList">
            <div className="downloadCard">
              <div className="downloadLeft">
                <a href="/exploration.zip" download className="downloadButton">
                  Download ZIP
                </a>
              </div>
              <div className="downloadRight">
                <h2>Pre-Experiment Coding</h2>
                <p>
                  This archive contains early exploratory coding completed before
                  the formal experiment stage. It includes random coding work done
                  with my professor to study the effects of different marginal
                  structures and related ideas.
                </p>
              </div>
            </div>
  
            <div className="downloadCard">
              <div className="downloadLeft">
                <a href="/experiment.zip" download className="downloadButton">
                  Download ZIP
                </a>
              </div>
              <div className="downloadRight">
                <h2>Experiment Files</h2>
                <p>
                  This archive contains the Python files used for the experiments
                  in my paper. Users can download these files and run the same
                  experiments themselves.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }