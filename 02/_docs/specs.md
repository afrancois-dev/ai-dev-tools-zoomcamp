# Mini Kanban Board — Technical Specification

**Version:** 1.0.0  
**Date:** September 14, 2026  
**Status:** Approved for MVP Development  

---

## 1. Executive Summary

This specification outlines the functional and technical requirements for a lightweight, single-board **Mini Kanban Board** application. The project aims to provide an intuitive task management workspace featuring fluid drag-and-drop interactions across custom status columns. The app name is KanbanLite.

---

## 2. Tech Stack Architecture

### Backend
* **Runtime & Package Manager:** Python (managed via `uv`)
* **Web Framework:** FastAPI
* **Data Persistence:** In-memory storage (volatile state for initial release)
* **API Style:** RESTful HTTP / JSON endpoints

### Frontend
* **Runtime Environment:** Node.js
* **UI Library:** React
* **Styling Framework:** Tailwind CSS
* **Drag-and-Drop Engine:** `@dnd-kit` (or `@hello-pangea/dnd`)

---

## 3. Data Models

### Column Model
```json
{
  "id": "string (UUID)",
  "title": "string",
  "order": "integer"
}
```

### Card Model
```json
{
  "id": "string (UUID)",
  "column_id": "string (UUID)",
  "title": "string",
  "description": "string",
  "priority": "string (Low | Medium | High | Urgent)",
  "created_at": "string (ISO 8601)",
  "due_date": "string (ISO 8601 / YYYY-MM-DD)",
  "position": "integer"
}
```

---

## 4. Default Configurations

### Initial Board State
The application initializes with five default columns ordered sequentially:
1. **To Do**
2. **In Progress**
3. **Deployed in Staging**
4. **Deployed in Production**
5. **On Hold**

---

## 5. Key Features & Functional Requirements

### Board & Column Management
* **Single Board Context:** Simplified interface focusing on a single, primary board workspace.
* **Dynamic Column Creation:** Ability to append custom columns dynamically at runtime.
* **Open Access:** Unauthenticated access for rapid development and testing.

### Interactive Card Operations
* **Card Attributes:** Track `Title`, `Description`, `Priority`, `Created Timestamp`, and `Due Date`.
* **Full Drag-and-Drop Support:**
  * **Inter-column Transfer:** Move cards freely between different status columns.
  * **Intra-column Reordering:** Adjust vertical card positioning within the same column.

---

## 6. Scope Boundaries (MVP Exclusions)

To maintain a focused scope for the initial release, the following items are deferred:
* Persistent database layer (SQLite / BigQuery / PostgreSQL integration).
* Search, filtering, and tag-based query controls.
* Multi-board workspace management.
* WebSockets or real-time state synchronization across multiple client sessions.