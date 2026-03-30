import { useEffect, useRef } from "react";
import * as PIXI from "pixi.js";
import { CANVAS } from "../config/layout";
import { drawAllCharacters } from "./drawCharacters";
import { drawRoomLabels, drawFooterLabels } from "./drawLabels";

const DESIGN_W = CANVAS.WIDTH;
const DESIGN_H = CANVAS.HEIGHT;

export function OfficeCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let app: PIXI.Application;
    let ro: ResizeObserver | null = null;

    (async () => {
      app = new PIXI.Application();
      await app.init({
        width: DESIGN_W,
        height: DESIGN_H,
        background: 0x2a2420,
        antialias: false,
        resolution: 1,
      });

      const container = mountRef.current;
      if (!container) return;
      container.appendChild(app.canvas);

      // ── 배경 이미지 (office-room.png) ──────────────────────────────────
      const bgTexture = await PIXI.Assets.load("/office-room.png");
      const bg = new PIXI.Sprite(bgTexture);
      bg.width = DESIGN_W;
      bg.height = DESIGN_H;
      app.stage.addChild(bg);

      // ── 캐릭터 오버레이 ────────────────────────────────────────────────
      const charGfx = new PIXI.Graphics();
      app.stage.addChild(charGfx);
      drawAllCharacters(charGfx);

      // ── 라벨 오버레이 ──────────────────────────────────────────────────
      const labelContainer = new PIXI.Container();
      app.stage.addChild(labelContainer);
      drawRoomLabels(labelContainer);
      drawFooterLabels(labelContainer);

      // ── 반응형 스케일링 ────────────────────────────────────────────────
      function resize() {
        if (!container) return;
        const cw = container.clientWidth;
        const ch = container.clientHeight;
        const scale = Math.min(cw / DESIGN_W, ch / DESIGN_H);
        app.renderer.resize(DESIGN_W * scale, DESIGN_H * scale);
        app.stage.scale.set(scale);
      }

      ro = new ResizeObserver(resize);
      ro.observe(container);
      resize();
    })();

    return () => {
      ro?.disconnect();
      app?.destroy(true);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        width: "100%",
        height: "100%",
        imageRendering: "pixelated",
      }}
    />
  );
}
