import { useRef, useState } from "react"
import { useRouter } from "next/router"

interface Props {
  videoUrl: string
  jobId: string
  campaignId?: string
  onNewAd: () => void
}

export default function VideoResult({ videoUrl, jobId, campaignId, onNewAd }: Props) {
  const router = useRouter()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [copied, setCopied] = useState(false)


  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const fullUrl = videoUrl?.startsWith('http') ? videoUrl : `${apiUrl}${videoUrl}`

  const handleDownload = () => {
    const a = document.createElement("a")
    a.href = fullUrl
    a.download = `creoad_ad_${jobId.slice(0,8)}.mp4`
    a.click()
  }

  const handleCopyLink = () => {
    navigator.clipboard.writeText(fullUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 14,
      overflow: "hidden",
      boxShadow: "none",
      maxWidth: 780
    }}>

      {/* Header */}
      <div style={{
        padding: "14px 20px",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(255, 255, 255, 0.03)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28,
            background: "rgba(22, 163, 74, 0.2)",
            color: "#4ade80",
            borderRadius: "50%",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14
          }}>✓</div>
          <div>
            <div style={{
              fontSize: 14, fontWeight: 700, color: "var(--text)",
              fontFamily: "DM Mono, monospace"
            }}>
              AD READY
            </div>
            <div style={{ fontSize: 11, color: "#888", marginTop: 1 }}>
              Job {jobId.slice(0, 8)} · TV 1920×1080
            </div>
          </div>
        </div>
        <span style={{
          background: "#dcfce7",
          color: "#16a34a",
          fontSize: 10,
          fontWeight: 700,
          padding: "3px 10px",
          borderRadius: 20,
          fontFamily: "DM Mono, monospace"
        }}>
          COMPLETE
        </span>
      </div>

      {/* Video Player */}
      <div style={{
        background: "#0a0a0a",
        position: "relative",
        aspectRatio: "16/9"
      }}>
        <video
          ref={videoRef}
          src={fullUrl}
          controls
          style={{ width: "100%", height: "100%", display: "block" }}
          poster=""
        >
          Your browser does not support video.
        </video>
      </div>

      {/* Actions */}
      <div style={{
        padding: "16px 20px",
        display: "flex",
        gap: 10,
        borderTop: "1px solid #e8e6e0",
        flexWrap: "wrap"
      }}>
        {/* Download */}
        <button
          onClick={handleDownload}
          style={{
            background: "#0a0a0a",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 7,
            fontFamily: "DM Sans, sans-serif"
          }}
        >
          ⬇ Download MP4
        </button>

        {/* Copy link */}
        <button
          onClick={handleCopyLink}
          style={{
            background: "transparent",
            color: "#0a0a0a",
            border: "1.5px solid #0a0a0a",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "DM Sans, sans-serif"
          }}
        >
          {copied ? "✓ Copied!" : "🔗 Copy link"}
        </button>

        {/* Edit */}
        <button
          onClick={() => router.push(`/editor?campaign_id=${campaignId}`)}
          style={{
            background: "transparent",
            color: "#4f46e5",
            border: "1.5px solid #4f46e5",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "DM Sans, sans-serif"
          }}
        >
          ✏ Edit ad
        </button>


        {/* New ad */}
        <button
          onClick={onNewAd}
          style={{
            background: "#ff5500",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            marginLeft: "auto",
            fontFamily: "DM Sans, sans-serif"
          }}
        >
          + New ad
        </button>
      </div>

      {/* Video info bar */}
      <div style={{
        padding: "10px 20px",
        background: "#f5f5f3",
        borderTop: "1px solid #e8e6e0",
        display: "flex",
        gap: 20,
        fontSize: 11,
        color: "#888",
        fontFamily: "DM Mono, monospace"
      }}>
        <span>FORMAT: TV 1920×1080</span>
        <span>CODEC: H.264</span>
        <span>FPS: 30</span>
        <span>DURATION: 30s</span>
        <span style={{ marginLeft: "auto" }}>
          <a
            href={fullUrl}
            target="_blank"
            rel="noreferrer"
            style={{ color: "#4f46e5", textDecoration: "none" }}
          >
            Open in new tab ↗
          </a>
        </span>
      </div>
    </div>
  )
}
