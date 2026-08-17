# Unifying Work Tracking with GitOps: Azure Boards & GitHub Integration Guide
This guide establishes a robust, zero-cost, enterprise-grade **Dual-Plane Software Delivery Lifecycle (SDLC)** [2]. It bridges your collaborative visual agile boards with your version-controlled GitHub repository under our strict **Everything-as-Code (EaC)** paradigm [1].

---

## 🏗️ THE DUAL-PLANE ARCHITECTURE
In a high-performing engineering organization, we maintain a strict boundary between our planning and execution environments [1]. 

```
  [ NON-DEVELOPERS & PMs ]                 [ DEVELOPERS & AI AGENTS ]
      100% Web Browser                         100% IDE / Code / Git
┌───────────────────────────┐             ┌───────────────────────────────┐
│     The Product Plane     │             │        The Code Plane         │
│   - Manage Epics & Sprints│             │   - Local LLM Agent Coding    │
│   - Write User Stories    │   Sync      │   - Pre-Commit Validation     │
│   - Define Acceptance     │ <─────────> │   - Automated PR Generation   │
│     Criteria              │  Webhooks   │   - Documentation updates     │
│   - Drag & Drop Boards    │             │   - Git as Source of Truth    │
└───────────────────────────┘             └───────────────────────────────┘
```

Non-technical stakeholders operate 100% inside their visual web browser using **Azure Boards** [5], while developers and local AI agents execute 100% inside their IDE and terminal. They communicate seamlessly using Git event-driven integrations without manual double-entry or administrative overhead [1, 4].

---

## 📊 AZURE BOARDS FREE TIER: LIMITS & ALIGNMENTS

Azure DevOps Services operates on a generous freemium licensing model designed for small teams and homelabs [2].

### 1. The Licensing Quotas & Performance Guardrails
*   **Basic User Licenses:** First **5 users are free** [2]. Basic users get full, unrestricted access to Azure Repos, Pipelines, and advanced Board capabilities [2].
*   **Stakeholder Access:** **Unlimited users are free** [2]. This is ideal for business sponsors, clients, or observers who need work-tracking visibility but do not commit code [3].
*   **Azure Artifacts:** **2 GiB of package storage free** per organization.
*   **Microsoft-Hosted Pipelines:** **1 free parallel job** (capped at 1,800 build minutes per month).
*   **Self-Hosted Pipelines:** **1 free concurrent job** with unlimited monthly build minutes.

### 2. Stakeholder Access Restrictions (Private Projects)
In private project workspaces, users assigned to the free **Stakeholder** tier are restricted in how they interact with the boards to ensure licensing compliance [2, 3]:
*   ❌ **No Drag-and-Drop Column Transitions:** Stakeholders cannot drag cards between status columns or drag items within a backlog to change priority order [2, 3].
*   ❌ **No Custom Tag Creation:** Stakeholders can apply pre-existing tags to work items, but they are blocked from creating new tag categories [2, 3].
*   ❌ **No Code-Plane Visibility:** Stakeholders cannot access the Repos or Pipelines interfaces [2].

#### 💡 The Stakeholder Workaround
To change a card's status without drag-and-drop permissions, the Stakeholder simply **double-clicks the card to open the full form**, selects the new state from the **State** dropdown, and clicks **Save & Close** [3].

---

## 🔌 CONNECTING GITHUB REPOS TO AZURE BOARDS

To establish bidirectional event-driven synchronization, you must connect your GitHub repository using the official, native **Azure Boards app** on GitHub [4, 5, 6].

### Step 1: Initialize Your Free Azure DevOps Workspace Safely
1.  Go to [dev.azure.com](https://dev.azure.com) in a fresh browser session and sign in with your Microsoft account.
2.  Create a new organization and project.
3.  ⚠️ **Critical Safety Step:** **Skip the billing connection step**. Do not attempt to link an active Azure Free Trial subscription, as it is ineligible for Azure DevOps billing and will throw an invalid offer code error. Skipping billing ensures your workspace remains strictly inside the zero-cost free tier forever.

### Step-by-Step GitHub App Connection Setup
1.  Go to the GitHub Marketplace and search for **\"Azure Boards\"** [6].
2.  Click **Install** and select whether to grant access to all repositories or only specific repositories (e.g. `k3s-lab`) [6].
3.  You will be redirected back to Azure DevOps to authenticate and map your GitHub repository to your Azure Boards project [5, 6].

---

## ⚡ COMMIT & BRANCH REFERENCE STANDARDS

Once the integration is healthy, the entire workflow lifecycle is driven by developer actions inside their local workstation environment [6]:

### 1. Linking Commits and Pull Requests
To link an asset, simply include the tag **`AB#<WorkItemId>`** inside your commit message or pull request description [4, 6]:
*   *Commit message example:*
    ```bash
    git commit -m "feat(infra): integrate external dns solver webhook AB#2048"
    ```
    *Result:* The commit hash, message, and author are instantly surfaced on the visual card [4, 6].
*   *Pull Request description example:*
    ```markdown
    ## Pull Request Title
    Fix authentication timeout issue

    ## Pull Request Description
    This PR resolves the token refresh failure.
    Related work items:
    - AB#1234
    ```
    *Result:* The pull request status, draft state, review approvals, and CI check statuses are updated dynamically on the card in real-time [4, 6].

### 2. Automating State Transitions
You can automatically transition the status of cards directly from Git by prefixing the `AB#` reference with a transition verb [4, 6]:
*   **`Fix AB#<ID>` / `Fixes AB#<ID>` / `Fixed AB#<ID>`:** Automatically transitions the work item to the first state defined under the **Resolved** (or **Completed**) category in your process template [4].
*   **`Closed AB#<ID>` / `Close AB#<ID>`:** Automatically transitions the card to the **Closed** state [4].

---

## 🛠️ TROUBLESHOOTING & COMMON PITFALLS

### 1. The Single-Organization Mapping Constraint
⚠️ **A GitHub repository can only be connected to ONE Azure DevOps organization and project at a time** [4, 5]. 
If you accidentally connect the same GitHub repository to multiple organizations (e.g., during testing or migration), the `AB#` parsing engine will encounter conflicts, resulting in duplicate processing failures and linking delays [4, 5].

### 2. Legacy Webhook Conflicts
If you recently migrated or transitioned connection types, older repository-level webhooks can remain active and conflict with the native GitHub App [11].
*   Go to your **GitHub Repository -> Settings -> Webhooks** [11].
*   Look for any legacy webhooks pointing to an Azure DevOps URL (e.g., `https://dev.azure.com/.../_apis/work/events`) [11].
*   **Delete any legacy webhooks** to prevent duplicate event processing loops [11].

### 3. Re-triggering App Synchronization
If branches created from the Azure Boards UI display correctly, but commits or pull requests fail to update the development panel, the backend synchronization queue may have drifted [11].
*   In Azure DevOps, navigate to **Project Settings -> GitHub Connections** [5, 11].
*   Click the action menu (three dots) next to the connected repository and select **Remove repository** [11].
*   Re-add the repository immediately [11]. This forces Azure DevOps to send a fresh registration event to the GitHub App installation matrix and clears the queue [11].

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
