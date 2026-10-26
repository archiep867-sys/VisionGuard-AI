# VisionGuard AI — Technical Report (submission draft)

## Problem and intended impact

Video operators may need help prioritizing review of activity in a marked restricted area. VisionGuard is a prototype that flags sustained motion in a configured region and assembles evidence for a human reviewer. The intended benefit is faster triage, not autonomous enforcement.

## Users

Potential users include safety officers and facility operators reviewing recorded footage. The prototype is not validated for operational deployment and should not be used for consequential decisions without extensive validation and human oversight.

## Method and OpenCV 5 implementation

The app samples frames from a user-provided video. OpenCV 5 performs video decoding, MOG2 background subtraction, morphological filtering, region-of-interest masking, contour filtering, and annotation. Foreground motion within the configured polygon is measured in pixels. A rule-based agent reacts to initial evidence by inspecting subsequent samples and only records a confirmed motion candidate after the persistence threshold is reached.

## Agent workflow

Perception → threshold decision → follow-up sampling → persistence check → incident candidate or close observation → human review. The agent trace is displayed in the UI and included in the downloadable report. The follow-up action is conditioned on the visual result, rather than a fixed chatbot response.

## Cloud architecture

The Streamlit application can run locally or as a Docker service on Render. The optional AWS S3 integration archives the JSON report using boto3. The competition requirement calls for a meaningful component on AWS; the S3 archive is intended to satisfy this only after a real bucket upload is configured and demonstrated. Include a screenshot or log proving successful upload in the final submission.

## Evaluation

No performance claims are made in this starter package. Evaluate on a labeled set of consented clips. Record true positives, false positives, false negatives, processing latency, clip duration, and the threshold settings. Include at least one failure case and explain why it failed. The provided pytest is a smoke test, not a complete accuracy evaluation.

## Limitations and responsible use

Motion can be caused by shadows, camera movement, lighting changes, or harmless activity. The default region is illustrative and must be calibrated for the scene. The prototype does not identify people, detect PPE, understand context, or prove a violation. Use consented footage, minimize retention, secure S3 access, and require human verification. Do not use it for sole-source employment, disciplinary, or emergency decisions.

## Required evidence before submission

1. Runtime output showing `cv2.__version__` is 5.x.
2. Actual local/cloud run on test footage.
3. Actual S3 upload evidence, if claiming AWS archive integration as deployed.
4. Evaluation table with measured results and failure cases.
5. Public/private judge-accessible repository, architecture diagram, and <=5-minute demo video.
