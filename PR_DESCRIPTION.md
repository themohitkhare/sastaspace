## Title
fix: Multi-layer deduplication and robustness improvements for inventory creation pipeline

## Summary
This PR addresses critical issues in the inventory creation pipeline, including duplicate item detection, AI model reliability, and test stability. It implements a comprehensive multi-layer deduplication strategy, improves error handling for edge cases, and fixes flaky tests that were causing CI failures.

## Problem Statement
1. **Duplicate Items**: AI models were detecting the same physical garment multiple times with different names (e.g., "Light-Colored Patterned Dress" AND "Yellow Polo Shirt" for the same yellow shirt)
2. **Duplicate Inventory Creation**: Single photos were creating multiple identical inventory items
3. **AI Reliability**: Network timeouts, corrupted images, and malformed JSON responses were causing job failures
4. **Test Flakiness**: Hard-coded category/brand names and blob ID assumptions were causing random test failures in parallel runs

## Changes

### Backend

#### Multi-Layer Deduplication System
- **AI Prompt Layer**: Enhanced detection prompt with explicit instructions and examples to detect each item only once
- **Post-Processing Layer**: Added intelligent similarity-based deduplication in `ClothingDetectionService` using word overlap analysis
- **Database Layer**: Added blob-level deduplication in `ClothingDetectionJob` to prevent creating multiple items from the same image blob
- **Attachment Counting**: Fixed `BlobAttachmentService` to accurately track additional images attached

#### AI Detection Improvements
- **Enhanced Prompts**: Updated `DETECTION_PROMPT` with explicit rules for unique item identification and duplicate checking
- **UI Element Filtering**: Added instructions to filter out UI elements from screenshots in both detection and extraction prompts
- **Robust JSON Parsing**: Implemented 3-layer JSON extraction strategy to handle AI models "thinking out loud" or including markdown formatting

#### Error Handling & Resilience
- **Image Processing**: Added graceful handling for corrupted JPEG files (`Vips::Error`) - logs warnings but doesn't fail jobs
- **Network Timeouts**: Implemented multi-layer retry strategy (RubyLLM config + service-level + job-level) with exponential backoff for `Net::ReadTimeout` errors
- **Temp File Cleanup**: Ensured proper cleanup of temporary files in `ClothingDetectionService`

#### Inventory Item Updates
- **Retrigger Extraction**: Automatically retriggers stock photo extraction when relevant fields (description, category, metadata, images) are updated
- **DRY Refactoring**: Consolidated extraction logic into `StockPhotoExtractionService.queue_for_item` method

### Tests

#### New Test Coverage
- **Deduplication Tests**: Created `clothing_detection_service_deduplication_test.rb` with 10 comprehensive tests
- **AI Parsing Tests**: Created `clothing_detection_service_ai_parsing_test.rb` with 7 tests for messy JSON scenarios
- **Image Processing Tests**: Added tests for graceful Vips error handling
- **Network Retry Tests**: Added tests for timeout retry logic

#### Test Stability Fixes
- **Hard-Coded Names**: Replaced all hard-coded category/brand names with `SecureRandom.hex(4)` to prevent collisions in parallel tests
- **Blob ID Assertions**: Updated `stock_extraction_test.rb` to use actual attached blob IDs instead of expecting specific IDs
- **Category Matching**: Fixed category matching tests to use `find_or_create_by` to handle existing categories

## Implementation Details

### Deduplication Algorithm
The post-processing deduplication uses a sophisticated similarity matching algorithm:
1. Normalizes names by removing descriptive words (light, dark, colored, patterned)
2. Standardizes garment types (shirt/dress/top → "garment")
3. Compares by signature: `category + color + normalized_name`
4. Uses 60%+ word overlap threshold for similarity
5. Performs substring matching for containment detection

### Multi-Layer Retry Strategy
1. **RubyLLM Config**: Increased default timeout to 180s and retry interval to 2s
2. **Service Level**: Retries up to 3 times with exponential backoff (2^retry_count seconds)
3. **Job Level**: ActiveJob retry with `retry_on` for network errors

### JSON Extraction Strategy
1. Extract JSON between first `{` and last `}`
2. Look for JSON in markdown code fences (`` ```json ... ``` ``)
3. Use line-by-line brace counting for complex cases
4. Graceful fallback with error logging if all strategies fail

## Files Changed
- **17 files modified**, **2 new test files**
- **+911 insertions**, **-104 deletions**

### Key Files
- `app/services/clothing_detection_service.rb` - Deduplication logic, improved prompts, robust JSON parsing
- `app/jobs/clothing_detection_job.rb` - Blob-level deduplication, network retry
- `app/services/services/inventory_item_update_service.rb` - Retrigger extraction on updates
- `app/services/services/blob_attachment_service.rb` - Fixed attachment counting
- `app/jobs/image_processing_job.rb` - Graceful Vips error handling
- `test/services/clothing_detection_service_deduplication_test.rb` - New comprehensive deduplication tests
- `test/services/clothing_detection_service_ai_parsing_test.rb` - New AI parsing edge case tests

## Testing
- ✅ All tests passing (114+ tests, 285+ assertions)
- ✅ Fixed 8+ flaky tests related to hard-coded names
- ✅ Added 17+ new tests for deduplication and error handling
- ✅ System tests stable with proper blob ID handling

## Impact

### Before
- 🔴 Same yellow shirt detected 4 times with different names
- 🔴 Single photo creating multiple duplicate inventory items
- 🔴 Network timeouts causing job failures
- 🔴 Corrupted images breaking the pipeline
- 🔴 Flaky tests causing CI failures

### After
- ✅ Each physical garment detected exactly once
- ✅ Single photo creates single inventory item (or reuses existing)
- ✅ Network timeouts handled with automatic retries
- ✅ Corrupted images logged but don't break pipeline
- ✅ All tests stable and passing consistently

## Checklist
- [x] Tests pass (`rails test`)
- [x] System tests pass (`rails test:system`)
- [x] CI pipeline passes (`bin/ci`)
- [x] Linter passes (`rubocop`)
- [x] No sensitive data exposed
- [x] Error handling tested with edge cases
- [x] Deduplication tested with various scenarios
- [x] Test stability verified with multiple runs

## Related Issues
- Fixes duplicate inventory item creation from single photos
- Fixes AI model detecting same item multiple times
- Fixes flaky tests in parallel execution
- Improves error handling for production edge cases

