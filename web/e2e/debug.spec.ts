import { test } from "@playwright/test";
import * as fs from "fs";

test("check button computed styles", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("http://localhost:3000/example-com");
  await page.waitForSelector("button[type=submit]", { timeout: 5000 });

  const info = await page.evaluate(() => {
    const btn = document.querySelector("button[type=submit]") as HTMLElement;
    const style = window.getComputedStyle(btn);
    const htmlStyle = window.getComputedStyle(document.documentElement);
    return {
      buttonHeightPx: btn.getBoundingClientRect().height,
      computedHeight: style.height,
      paddingTop: style.paddingTop,
      paddingBottom: style.paddingBottom,
      borderTop: style.borderTopWidth,
      borderBottom: style.borderBottomWidth,
      htmlFontSize: htmlStyle.fontSize,
      spacingVar: htmlStyle.getPropertyValue("--spacing").trim(),
      buttonClasses: btn.className,
    };
  });
  fs.writeFileSync("/tmp/button-debug.json", JSON.stringify(info, null, 2));
});
