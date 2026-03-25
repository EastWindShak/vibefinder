/**
 * Get the best available thumbnail URL for a song.
 * Falls back to YouTube's default thumbnail if no thumbnail_url is provided.
 * 
 * YouTube thumbnail URL patterns:
 * - default.jpg: 120x90
 * - mqdefault.jpg: 320x180
 * - hqdefault.jpg: 480x360
 * - sddefault.jpg: 640x480
 * - maxresdefault.jpg: 1280x720 (not always available)
 */

export type ThumbnailQuality = 'default' | 'mq' | 'hq' | 'sd' | 'maxres'

export function getYouTubeThumbnailUrl(videoId: string, quality: ThumbnailQuality = 'hq'): string {
  const qualityMap = {
    default: 'default.jpg',
    mq: 'mqdefault.jpg',
    hq: 'hqdefault.jpg',
    sd: 'sddefault.jpg',
    maxres: 'maxresdefault.jpg'
  }
  return `https://img.youtube.com/vi/${videoId}/${qualityMap[quality]}`
}

export function getThumbnailUrl(
  thumbnailUrl: string | undefined,
  videoId: string | undefined,
  quality: ThumbnailQuality = 'hq'
): string | null {
  // If we have a thumbnail URL, use it
  if (thumbnailUrl) {
    return thumbnailUrl
  }
  
  // If we have a video ID, use YouTube's default thumbnail
  if (videoId) {
    return getYouTubeThumbnailUrl(videoId, quality)
  }
  
  // No thumbnail available
  return null
}

/**
 * Component helper to handle thumbnail loading with fallback.
 * Returns the primary URL and a fallback URL.
 */
export function getThumbnailWithFallback(
  thumbnailUrl: string | undefined,
  videoId: string | undefined
): { primary: string | null; fallback: string | null } {
  const primary = thumbnailUrl || null
  const fallback = videoId ? getYouTubeThumbnailUrl(videoId, 'hq') : null
  
  return {
    primary: primary || fallback,
    fallback: primary ? fallback : null
  }
}
