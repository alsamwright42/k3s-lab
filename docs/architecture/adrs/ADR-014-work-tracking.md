# ADR 014: Agile Planning and Work Tracking Architecture

## Status
**Active**

## Context
As the homelab cluster and codebase scale toward an enterprise-grade posture, we must establish a structured, automated, and collaborative Software Delivery Lifecycle (SDLC) [1]. This requires choosing a work tracking and project management plane that bridges the gap between non-technical stakeholders (Product Plane) and engineers or local AI agents (Code Plane) [1].

Historically, manual planning mechanisms ("ClickOps") and localized tracking methods (such as flat markdown files or disconnected project boards) have introduced severe operational friction, duplicate data entry, and traceability drift [1]. To resolve this, we evaluated several options against our strict Everything-as-Code (EaC) and GitOps principles, under the following constraints:
1. **Azure & C# Alignment:** The platform must natively support and align with Microsoft Azure and .NET Core methodologies to cement professional mastery for enterprise C# shops.
2. **Cost & Scale Boundaries:** The solution must provide a generous, permanent free tier for a small team, without arbitrary limitations on automated pipeline triggers or API access.
3. **Declarative Provisioning:** The workspace configurations, repository mappings, and branch protection rules must be fully auditable and manageable as code (Infrastructure-as-Code) [1, 7].
4. **Automated Event Synchronization:** Ticket lifecycle states, commits, and pull requests must reconcile automatically through version control events, eliminating manual browser administrative overhead [1].

### Evaluated Alternatives

#### 1. Atlassian Jira Cloud (Free Tier)
Jira is a highly customizable project management platform [8]. However, its free tier possesses several critical limitations for enterprise-style GitOps workflows:
* **User Ceiling:** Strictly capped to 10 users [8].
* **Automation Limits:** Gated to a severe limit of 100 execution runs per month across the organization, which is easily exhausted by high-frequency developer/agent Git pushes [8, 9].
* **Security & Role Governance:** Custom roles and granular permissions are completely disabled on Jira Free; all workspace users are granted global administrator rights by default, presenting a major operational risk [8].
* **IaC Restrictions:** While community Terraform providers exist, deploying custom permission schemes, team role mappings, or issue security configurations via Terraform fails or throws API errors on the free plan [8].

#### 2. Local-First / Git-Embedded Trackers (`git-bug` / `git-native-issue`)
These CLI-driven frameworks store the planning ledger directly within the Git object database using custom namespaces (e.g., `refs/bugs/` or `refs/issues/`) [1].
* **Pros:** Complete offline capability, absolute data sovereignty, zero external API dependencies, and no vendor lock-in [1].
* **Cons:** Lack of a centralized, hosted web interface excludes non-technical business stakeholders (such as product managers, designers, or clients) who cannot run terminal commands, breaking team collaboration [1].

#### 3. Azure Boards (Azure DevOps Services Free Tier)
Azure Boards is Microsoft's enterprise agile planning tool [5]. It offers native integrations with GitHub and deeply aligns with the Microsoft ecosystem [5].
* **Basic User Quota:** The first 5 users receive full **Basic** access level licenses at $0 [2]. Additional active developers cost $6 per user/month.
* **Stakeholder Quota:** Provides **unlimited** free **Stakeholder** licenses for business owners, clients, and observers [2].
* **Automation Depth:** Offers unlimited project-level custom automation rules and queries without monthly execution limits.
* **Configuration-as-Code:** Highly extensible and manageable via the officially maintained Microsoft `azuredevops` Terraform provider [7].

---

## Decision
We will standardize on **Azure DevOps Services (Azure Boards)** as our primary agile planning and work tracking workspace, connected bidirectionally to our **GitHub repository** via the native, first-party **Azure Boards GitHub App** [5, 6].

This architecture establishes a **Dual-Plane Software Delivery Lifecycle (SDLC)**:

```
  [ PRODUCT PLANE ]                         [ CODE PLANE ]
Azure Boards (Web GUI) ──[GitHub App Sync]──> GitHub Repository (Git / IDE)
 - Epics, Stories, Bugs                     - Conventional Branches
 - Acceptance Criteria                      - pre-commit Quality Gates
 - Stakeholder Progress                     - AB#<ID> Traceability Hooks
```

### Technical Integration Blueprint

### 1. Declarative Platform Provisioning
We will manage the workspace, project settings, repository service connections, and branch protection policies declaratively using Terraform and the official Microsoft provider:
```hcl
terraform {
  required_providers {
    azuredevops = {
      source  = \"microsoft/azuredevops\"
      version = \"~> 1.15\"
    }
  }
}

resource \"azuredevops_project\" \"homelab\" {
  name               = \"k3s-lab\"
  visibility         = \"private\"
  version_control    = \"Git\"
  work_item_template = \"Agile\"
  features = {
    \"boards\"       = \"enabled\"
    \"repositories\" = \"enabled\"
    \"pipelines\"    = \"enabled\"
    \"artifacts\"    = \"enabled\"
    \"testplans\"    = \"disabled\"
  }
}
```

### 2. Git-to-Board Event Traceability
We will utilize the secure Azure Boards GitHub App to intercept VCS events and synchronize development metadata natively with work items [5].

* **Linkage Syntax:** Developers and local AI coding agents will reference work items in commit messages and pull request descriptions using the standard `AB#<ID>` syntax (e.g., `git commit -m \"feat(infra): deploy Vaultwarden ingress AB#14\"`) [4, 6].
* **State Transition Verbs:** We will enable automatic status transitions by prepending recognized verbs (such as `Fixed`, `Closed`, or `Resolved`) to the work item key in default branch merges (e.g., `Fixes AB#14`) [4]. This automatically advances the board status card through the workflow [4].
* **Repository Isolation:** To ensure predictable sync behaviors, the GitHub repository must be mapped strictly to **one** Azure DevOps organization at a time [4, 5].

### 3. Stakeholder Management & Workspace Workaround
To operate at zero cost across teams larger than five members, business observers will be assigned the free **Stakeholder** access level [2]. To address the native private-project restriction where Stakeholders cannot drag-and-drop cards on the Kanban board [2, 3], we establish the following operational workaround:
* Stakeholders must **double-click/open the work item form** in their browser to edit fields.
* They can manually select the **State** dropdown menu inside the card details and save, successfully transitioning issues without requiring a paid Basic license [3].

---

## Consequences

### Positive (Consequences)
* **Everything-as-Code (EaC):** The agile tracking environment is codified, version-controlled, and synchronized programmatically via Terraform [7].
* **Absolute Traceability:** Provides auditors and engineering leads with a complete, tamper-proof history connecting every user story directly to specific branches, commits, PRs, and build pipelines [1].
* **No Platform Overhead:** Developers remain 100% inside their IDE/Git interfaces while work items update dynamically in the background [1].
* **No Scripting Quotas:** Unlimited local and project-level automations bypass Atlassian's restrictive 100-run monthly limit [8, 9].
* **Zero Cost Platform:** Enables unlimited stakeholders to collaborate on private projects with zero license fees by utilizing the card-form state modification workaround [2, 3].

### Negative (Consequences)
* **Administrative Setup:** Requires a one-time configuration of the GitHub App, subscription scoping, and Terraform provisioning [6, 11].
* **Private Project UI Restrictions:** Non-technical Stakeholders must be explicitly trained to use the form-dropdown workaround to transition states, rather than dragging cards across the visual board [2, 3].
* **Single-Org Bound:** Restricts our GitHub repository to a single Azure DevOps organization mapping to avoid duplicate sync loops and processing errors [4, 5].

---

## References

* **[1] Everything as Code (EaC) Taxonomy:** Wei, H., Madhavji, N., & Steinbacher, J. (2025). *Understanding Everything as Code: A Taxonomy and Conceptual Model*. arXiv:2507.05100. [https://arxiv.org/html/2507.05100v1](https://arxiv.org/html/2507.05100v1)
* **[2] Azure DevOps Access Levels:** Microsoft Learn. (2026). *About access levels - Azure DevOps Services*. [https://learn.microsoft.com/en-us/azure/devops/organizations/security/access-levels?view=azure-devops](https://learn.microsoft.com/en-us/azure/devops/organizations/security/access-levels?view=azure-devops)
* **[3] Get Started as a Stakeholder:** Microsoft Learn. (2026). *Get started with Stakeholder access - Azure DevOps*. [https://learn.microsoft.com/en-us/azure/devops/organizations/security/get-started-stakeholder?view=azure-devops](https://learn.microsoft.com/en-us/azure/devops/organizations/security/get-started-stakeholder?view=azure-devops)
* **[4] Link GitHub Objects to Azure Boards:** Microsoft Learn. (2026). *Link GitHub commits, pull requests, branches, and issues to work items in Azure Boards*. [https://learn.microsoft.com/en-us/azure/devops/boards/github/link-to-from-github?view=azure-devops](https://learn.microsoft.com/en-us/azure/devops/boards/github/link-to-from-github?view=azure-devops)
* **[5] Connect Azure Boards to GitHub:** Microsoft Learn. (2026). *Connect an Azure Boards or Azure DevOps project to a GitHub repository*. [https://learn.microsoft.com/en-us/azure/devops/boards/github/connect-to-github?view=azure-devops](https://learn.microsoft.com/en-us/azure/devops/boards/github/connect-to-github?view=azure-devops)
* **[6] Set Up Commit & PR Linking:** OneUptime. (2026). *How to Set Up Azure Boards GitHub Integration to Link Commits*. [https://oneuptime.com/blog/post/2026-02-16-how-to-set-up-azure-boards-github-integration-to-link-commits-and-pull-requests-to-work-items/view](https://oneuptime.com/blog/post/2026-02-16-how-to-set-up-azure-boards-github-integration-to-link-commits-and-pull-requests-to-work-items/view)
* **[7] Terraform DevOps Project Provisioning:** OneUptime. (2026). *How to Create Azure DevOps Projects in Terraform*. [https://oneuptime.com/blog/post/2026-02-23-how-to-create-azure-devops-projects-in-terraform/view](https://oneuptime.com/blog/post/2026-02-23-how-to-create-azure-devops-projects-in-terraform/view)
* **[8] Jira Pricing & Gated Features:** Carly AI. (2026). *Jira Pricing in 2026: Every Plan, the Per-User Slide, and Is Jira Free?*. [https://www.usecarly.com/blog/jira-pricing/](https://www.usecarly.com/blog/jira-pricing/)
* **[9] Jira Automation Limits:** eesel AI. (2026). *Is automation in Jira free? A complete 2026 guide*. [https://www.eesel.ai/blog/is-automation-in-jira-free](https://www.eesel.ai/blog/is-automation-in-jira-free)
* **[10] Conventional Branch Specification:** Conventional Branching Org. (2026). *Conventional Branch Specification (1.1.0)*. [https://conventionalbranch.org/](https://conventionalbranch.org/)
* **[11] GitHub-DevOps Sync Troubleshooting:** Microsoft Learn. (2026). *GitHub Pull Requests and Commits Not Appearing in Azure DevOps Work Item Development Section*. [https://learn.microsoft.com/en-in/answers/questions/5912402/github-pull-requests-and-commits-not-appearing-in](https://learn.microsoft.com/en-in/answers/questions/5912402/github-pull-requests-and-commits-not-appearing-in)
