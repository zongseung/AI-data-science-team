import { useEffect, useRef } from "react";
import * as PIXI from "pixi.js";
import { CANVAS } from "../config/layout";
import { drawBackground } from "./drawBackground";
import { drawFurniture } from "./drawFurniture";
import {
  drawRoomLabels,
  drawHeaderLabels,
  drawDashboardLabels,
  drawFooterLabels,
} from "./drawLabels";

export function OfficeCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let app: PIXI.Application;

    (async () => {
      app = new PIXI.Application();
      await app.init({
        width: CANVAS.WIDTH,
        height: CANVAS.HEIGHT,
        background: 0x0a0a12,
        antialias: false,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
      });

      if (mountRef.current) {
        mountRef.current.appendChild(app.canvas);
      }

      // 배경 (방·타일·복도·헤더·푸터·대시보드)
      const bgGfx = new PIXI.Graphics();
      app.stage.addChild(bgGfx);
      drawBackground(bgGfx);

      // 가구
      const furnitureGfx = new PIXI.Graphics();
      app.stage.addChild(furnitureGfx);
      drawFurniture(furnitureGfx);

      // 텍스트 레이블
      const labelContainer = new PIXI.Container();
      app.stage.addChild(labelContainer);
      drawRoomLabels(labelContainer);
      drawHeaderLabels(labelContainer);
      drawDashboardLabels(labelContainer);
      drawFooterLabels(labelContainer);
    })();

    return () => {
      app?.destroy(true);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        display: "inline-block",
        imageRendering: "pixelated",
        border: "1px solid #222233",
      }}
    />
  );
}
