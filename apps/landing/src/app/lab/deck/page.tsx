import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import landing from "../../landing.module.css";
import styles from "./deck.module.css";
import { Deck } from "./Deck";

export const metadata = {
  title: "deck — describe a project, get audio",
  description:
    "Describe a project in plain language and the deck drafts a track plan, then generates the audio. Open-source, local-first.",
};

export default function DeckPage() {
  return (
    <div className={landing.wrap}>
      <TopNav />
      <main className={styles.wrap}>
        <Deck />
      </main>
      <Footer />
    </div>
  );
}
