# Atelier Lens Backend Frontend Handoff

Base URL:

- local: `http://127.0.0.1:8000/api/v1`

## Auth

Member JWT header:

```http
Authorization: Bearer <accessToken>
```

Guest token header:

```http
Authorization: Bearer <guestToken>
```

Guest token creation:

- `POST /guest-sessions`

Member auth:

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`

## Job polling

Async APIs return `202` with:

```json
{
  "jobId": "uuid"
}
```

Poll:

- `GET /jobs/{jobId}`

Terminal states:

- `pending`
- `processing`
- `succeeded`
- `failed`

`result` and `error` are inside the job payload.

## Private file download

- `GET /files/{fileId}`
- Authorization required
- owner-only access

Frontend should never construct file storage paths manually. Only use `fileId`.

## Multipart APIs

- `POST /product-recognitions`
  - field: `image`
- `POST /try-ons`
  - field: `photo`
  - additional form fields: `scope`, `productId` or `savedCoordiId`, optional avatar overrides
- `POST /diagnoses`
  - field: `image`
  - form field: `registeredProductId`

## Main endpoint groups

Guest / Member shared:

- `POST /guest-sessions`
- `GET /products/{productId}`
- `GET /products/{productId}/variants`
- `GET /products/{productId}/recommendations`
- `POST /product-recognitions`
- `POST /avatar-try-ons`
- `POST /try-ons`
- `GET /jobs/{jobId}`
- `GET /files/{fileId}`

Member only:

- `GET /me`
- `PATCH /me`
- `POST /me/avatar`
- `GET /me/avatar`
- `PUT /me/avatar`
- `POST /try-ons/{tryOnId}/save`
- `GET /me/try-ons`
- `DELETE /me/try-ons/{tryOnId}`
- `POST /me/coordis`
- `GET /me/coordis`
- `GET /me/coordis/{savedCoordiId}`
- `PATCH /me/coordis/{savedCoordiId}`
- `DELETE /me/coordis/{savedCoordiId}`
- `POST /cart/items`
- `GET /cart`
- `PATCH /cart/items/{cartItemId}`
- `DELETE /cart/items/{cartItemId}`
- `POST /orders`
- `GET /me/orders`
- `GET /me/orders/{orderId}`
- `POST /me/products`
- `GET /me/products`
- `GET /me/products/{registrationId}`
- `GET /me/products/{registrationId}/care-guide`
- `POST /diagnoses`
- `GET /diagnoses/{diagnosisId}`
- `GET /diagnoses/{diagnosisId}/care-guide`
- `POST /repair-reservations`
- `GET /repair-reservations`
- `POST /repair-reservations/{repairReservationId}/cancel`

Guest avatar parameters:

- `PUT /guest-sessions/me/avatar-parameters`

## Common error codes

- `UNAUTHORIZED`
- `TOKEN_EXPIRED`
- `GUEST_SESSION_EXPIRED`
- `FORBIDDEN`
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `CONFLICT`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_FILE_TYPE`
- `GUEST_LIMIT_EXCEEDED`
- `PRODUCT_CODE_NOT_DETECTED`
- `PRODUCT_NOT_FOUND`
- `PRODUCT_CODE_AMBIGUOUS`
- `GENERATION_FAILED`
- `AI_UNAVAILABLE`
- `REPAIR_NOT_NEEDED`
- `REPAIR_SLOT_UNAVAILABLE`

## TTL behavior

- GuestSession: end of creation day in KST business rule
- source photo for photo try-on: 1 hour
- unsaved try-on result: 3 hours
- diagnosis source image: 24 hours
- job: 24 hours
- saved try-on result: no TTL
- source photo does not become permanent when result is saved

## Response envelope

Every endpoint returns:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "requestId": "req_xxx",
    "pagination": null
  }
}
```

Cursor pagination is currently used by:

- `GET /me/coordis`

## Current mocked features

- MockPayment
- MockTryOnProvider
- MockDiagnosisProvider

## Real-data / real-AI replacements still needed

- real MCM product code data for OCR refinement
- real virtual try-on provider
- real diagnosis provider
- real social OAuth provider exchange
