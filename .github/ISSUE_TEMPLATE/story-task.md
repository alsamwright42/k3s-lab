---
name: "📦 Story / Feature Task"
description: Standard development task, configuration change, or deployment
title: "Story: [Short Descriptive Title]"
labels: ["story"]
assignees: ""
---

## 📖 Context & User Story
> **As a** [System Operator / Developer]
> **I want to** [implement this configuration or deploy this service]
> **So that** [the cluster achieves this specific state/security stance]

## 🏗️ Architectural Boundary Alignment (ARD-004)
Identify which plane this task modifies to prevent tool collision:
- [ ] **Bare Metal / Host OS Layer (Bash / systemd)**
- [ ] **Cluster Layer (Declarative YAML / GitOps / Argo CD)**
- [ ] **Cloud Layer (Terraform / HCL)**

## 📋 Implementation Steps
Detailed, logical execution phases for this story:
- [ ] Create branch locally (`feature/issue-<num>-<desc>`)
- [ ] Draft declarative manifests or shell scripts
- [ ] Verify script with workstation shellcheck / linter gates
- [ ] Deploy and verify manually in staging/local node
- [ ] Commit and open Pull Request ("Closes #<num>")

## 🧪 Verification Plan
How do we prove this works?
```bash
# Provide the exact validation command

