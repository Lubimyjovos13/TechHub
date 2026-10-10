# TeachHub — Database Description

**Engine:** MongoDB (single database, name from env `DB_NAME`). Accessed async via Motor from FastAPI.
IDs are Mongo `ObjectId` (returned to the client as strings). Timestamps are ISO-8601 UTC strings.

---

## Collections

### 1. `users`
Registered accounts (teachers + admins).
| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `email` | string | **Unique index**, lowercased |
| `password_hash` | string | bcrypt hash (never returned by API) |
| `name` | string | Display name |
| `role` | string | `teacher` \| `admin` |
| `bio` | string | Profile description (≤500 chars) |
| `avatar_file_id` | string \| null | References `files.id` |
| `hide_followers` | bool | Hide followers list/count from others |
| `hide_following` | bool | Hide following list/count from others |
| `created_at` | string | ISO timestamp |

Indexes: `email` (unique).

### 2. `tasks`
Every published item ("post"). Three types via `type`.
| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `type` | string | `html` \| `worksheet` \| `blog` |
| `title` | string | Sanitized (tags stripped) |
| `subject` | string | one of 7 subjects |
| `grade` | string | one of 5 grade bands |
| `description` | string | ≤500 chars, sanitized |
| `html_code` | string \| null | For `html` type (≤1 MB), runs in sandboxed iframe |
| `body` | string \| null | For `blog` type (≤50 000 chars) |
| `files` | array | For `worksheet`/`blog`: `{file_id, url, original_filename, content_type, size, is_image}` |
| `folder_id` | string \| null | References a `folders._id` (author's organization) |
| `tags` | string[] | Up to 10 |
| `views` | int | Auto-increment on open |
| `likes_count` | int | Denormalized like counter |
| `is_draft` | bool | Drafts hidden from public; visible only to author/admin |
| `author_id` | string | References `users._id` |
| `created_at` / `updated_at` | string | ISO timestamps |

Indexes: `created_at` (desc), `type`.

### 3. `likes`
One like per user per task (powers one-like-per-user toggle).
| Field | Type | Notes |
|---|---|---|
| `user_id` | string | References `users._id` |
| `task_id` | string | References `tasks._id` |
| `created_at` | string | |

Indexes: compound **unique** `(user_id, task_id)`.

### 4. `favorites`
Saved posts per user.
| Field | Type | Notes |
|---|---|---|
| `user_id` | string | |
| `task_id` | string | |
| `created_at` | string | |

Indexes: compound **unique** `(user_id, task_id)`.

### 5. `follows`
Subscription graph (follower → following).
| Field | Type | Notes |
|---|---|---|
| `follower_id` | string | The user who follows |
| `following_id` | string | The user being followed |
| `created_at` | string | |

Indexes: compound **unique** `(follower_id, following_id)`.

### 6. `folders`
Author-created folders to organize their own posts in the Studio.
| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `user_id` | string | Owner |
| `name` | string | ≤60 chars |
| `subject` | string \| null | Optional category |
| `created_at` | string | |

(Auto folders "by type" / "by subject" are computed on the fly, not stored.)

### 7. `reports`
Content moderation reports handled by admins.
| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `task_id` | string | Reported post |
| `reporter_id` | string | Reporting user |
| `reason` | string | ≤500 chars, sanitized |
| `created_at` | string | |

### 8. `files`
Metadata for uploads (actual bytes live in Emergent object storage).
| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | **Unique index**; used in public URL `/api/files/{id}` |
| `storage_path` | string | Object-storage key |
| `original_filename` | string | |
| `content_type` | string | MIME type |
| `size` | int | Bytes |
| `owner_id` | string | Uploader |
| `is_image` | bool | Image vs document |
| `is_deleted` | bool | Soft-delete flag |
| `created_at` | string | |

Indexes: `id` (unique).

---

## Relationships (summary)
- `tasks.author_id` → `users._id`
- `tasks.folder_id` → `folders._id`
- `tasks.files[].file_id` / `users.avatar_file_id` → `files.id`
- `likes`, `favorites` → (`users._id`, `tasks._id`)
- `follows` → (`users._id` follower, `users._id` following)
- `reports.task_id` → `tasks._id`, `reports.reporter_id` → `users._id`

## Notes
- No raw Mongo documents are returned; serializers convert `_id`→`id` and strip `password_hash`.
- Deleting a user cascades: their tasks, likes, favorites, folders and follow edges are removed.
- Deleting a task cascades its likes, favorites and reports.
