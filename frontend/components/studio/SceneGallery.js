import React, { useEffect, useState } from 'react'

/**
 * SceneGallery — shows all generated scene images in a grid.
 * Visible even if the final video render fails, so the user
 * can inspect what ComfyUI actually produced.
 */
export default function SceneGallery({ campaignId, apiUrl }) {
  const [scenes, setScenes] = useState([])
  const [selectedScene, setSelectedScene] = useState(null)
  const API = apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (!campaignId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('creoad_token') : ''
    fetch(`${API}/api/ads/${campaignId}/scenes`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.scenes) setScenes(data.scenes)
      })
      .catch(() => {})
  }, [campaignId, API])

  if (scenes.length === 0) return null

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 16,
        boxShadow: 'none',
        marginTop: 16,
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 700,
          marginBottom: 12,
          fontFamily: 'DM Mono, monospace',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span>🎨</span>
        <span>GENERATED SCENES · {scenes.length} images</span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
          gap: 10,
        }}
      >
        {scenes.map((scene) => {
          const imgSrc = scene.imageUrl?.startsWith('http')
            ? scene.imageUrl
            : `${API}${scene.imageUrl}`
          return (
            <div
              key={scene.index}
              style={{
                border: '1px solid #e8e6e0',
                borderRadius: 8,
                overflow: 'hidden',
                cursor: 'pointer',
                transition: 'transform 0.15s, box-shadow 0.15s',
              }}
              onClick={() => setSelectedScene(scene)}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = ''
                e.currentTarget.style.boxShadow = ''
              }}
            >
              <div style={{ aspectRatio: '16/9', background: '#f5f5f3', position: 'relative' }}>
                {scene.status === 'done' && (
                  <img
                    src={imgSrc}
                    alt={`Scene ${scene.index + 1}`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    loading="lazy"
                  />
                )}
                {scene.status === 'generating' && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      fontSize: 11,
                      color: '#888',
                    }}
                  >
                    ⟳ Generating...
                  </div>
                )}
                {scene.status === 'failed' && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      fontSize: 11,
                      color: '#ef4444',
                    }}
                  >
                    ✗ Failed
                  </div>
                )}
              </div>
              <div style={{ padding: '6px 8px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, fontFamily: 'DM Mono, monospace' }}>
                  SC {String(scene.index + 1).padStart(2, '0')}
                </div>
                {scene.prompt && (
                  <div
                    style={{
                      fontSize: 9,
                      color: '#888',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {scene.prompt}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Lightbox modal */}
      {selectedScene && (
        <div
          onClick={() => setSelectedScene(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            cursor: 'zoom-out',
          }}
        >
          <img
            src={
              selectedScene.imageUrl?.startsWith('http')
                ? selectedScene.imageUrl
                : `${API}${selectedScene.imageUrl}`
            }
            alt={`Scene ${selectedScene.index + 1} full`}
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              borderRadius: 8,
              boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            }}
          />
        </div>
      )}
    </div>
  )
}
