# ADR 002: Application Manifest Directory Structure

## Status
Active

## Context
As Tier 5 (Applications) workloads are introduced into the repository, we must establish a scalable directory structure within the `manifests/apps/` path. Placing declarative YAML manifests directly into the root of the `manifests/apps/` directory creates a flat-file structure that becomes unmanageable as the cluster scales. It also complicates automated deployment scoping for GitOps controllers, which often require isolated paths per application.

## Decision
We will enforce a strict subfolder encapsulation pattern for all user workloads. All application manifests must be stored in a dedicated, named subdirectory under `manifests/apps/` (e.g., `manifests/apps/vaultwarden/vaultwarden.yaml`). Flat-filing manifests directly into the `manifests/apps/` root directory is prohibited. The same applies to the `manifests/base/' directory for infrastructure manifests.

## Consequences & Next Steps
* **Clean Boundaries:** This guarantees a contained boundary for application-specific resources (e.g., persistent volume claims, ingresses, and services).
* **GitOps Readiness:** Aligns with enterprise GitOps best practices, allowing our future controller (Argo CD or Flux) to target isolated application directory paths for granular synchronization.
* **Future Helm/Kustomize Migration:** Having dedicated folders prepares the application layout perfectly for when we transition these static YAML files into Kustomize overlays or local Helm charts. 
* **Action Item:** The `05_Repository_Structure.md` document must be updated to explicitly reflect this subfolder mandate.
