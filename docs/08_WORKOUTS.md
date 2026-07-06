# Phase 9: Workout Tracking

Phase 9 adds normalized workout tracking for sessions, exercises, and sets.

Core endpoints:

- `POST /api/v1/workouts`
- `GET /api/v1/workouts`
- `GET /api/v1/workouts/{workout_id}`
- `PATCH /api/v1/workouts/{workout_id}`
- `DELETE /api/v1/workouts/{workout_id}`
- `POST /api/v1/workouts/{workout_id}/exercises`
- `POST /api/v1/workouts/{workout_id}/exercises/{exercise_id}/sets`
- `GET /api/v1/workouts/progress/{exercise_name}`

Example create request:

```json
{
  "user_id": 1,
  "notes": "Push day",
  "exercises": [
    {
      "exercise_name": "bench press",
      "muscle_group": "chest",
      "sets": [
        {"set_number": 1, "reps": 10, "weight_kg": 50},
        {"set_number": 2, "reps": 8, "weight_kg": 55}
      ]
    }
  ]
}
```

Progress uses:

```text
estimated_1rm = weight_kg * (1 + reps / 30)
volume = weight_kg * reps
```

When a workout has a `user_id`, the service attempts to store a workout memory in Qdrant.
