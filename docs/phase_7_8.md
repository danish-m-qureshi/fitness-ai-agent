# Fitness AI Agent Phase 7 and 8

## Phase 7: Long-Term Memory

Phase 7 adds Qdrant as a local vector database and exposes memory endpoints under `/api/v1/memory`.

The backend uses Ollama embeddings with `EMBEDDING_MODEL_NAME`, defaulting to `nomic-embed-text`. Pull the model locally before using memory search:

```bash
ollama pull nomic-embed-text
```

Available endpoints:

- `POST /api/v1/memory`
- `POST /api/v1/memory/search`
- `DELETE /api/v1/memory/{memory_id}`

Meal and workout creation attempt to store memory automatically when a `user_id` is present. Memory write failures are logged but do not block core meal/workout persistence.

## Phase 8: Meal Image Analysis

Phase 8 adds the full meal-photo workflow under `/api/v1/meals/analyze-image`.

The endpoint accepts `multipart/form-data`:

- `file`: image upload
- `user_id`: existing user id
- `meal_type`: optional label such as `breakfast`, `lunch`, or `dinner`

The workflow:

1. Stores the uploaded image under `backend/storage/uploads/meals/`.
2. Sends the image to the configured local Ollama vision model.
3. Parses structured food detections.
4. Estimates nutrition using the local nutrition catalog.
5. Saves a meal and its food items to PostgreSQL.
6. Attempts to store a memory record in Qdrant.

The response always includes the disclaimer that image-based nutrition is an estimate, not medical or dietitian-grade calculation.
