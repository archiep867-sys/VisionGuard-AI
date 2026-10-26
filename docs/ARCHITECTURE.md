# Architecture

```mermaid
flowchart TD
  V[Video upload] --> O[OpenCV 5: decode and sample]
  O --> P[Foreground extraction and ROI mask]
  P --> D{Zone motion over threshold?}
  D -- No --> N[Log no-trigger decision]
  D -- Yes --> A[Agent requests follow-up samples]
  A --> C{Sustained motion?}
  C -- No --> X[Close observation window]
  C -- Yes --> I[Incident candidate + human review]
  N --> R[Annotated evidence and JSON/CSV report]
  X --> R
  I --> R
  R --> UI[Streamlit dashboard]
  R -. optional upload .-> S3[AWS S3 evidence archive]
```

## Trust boundaries

- Uploaded video is untrusted input; only process supported video formats and avoid unnecessary retention.
- AWS credentials must be provided through a secret manager/environment, never source control.
- S3 permissions should be limited to writing the designated report prefix.
- Alerts are suggestions for human review, not verified safety findings.
