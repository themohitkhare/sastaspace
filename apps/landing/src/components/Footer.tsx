import styles from "@/app/landing.module.css";

const SOCIAL = {
  github: "https://github.com/themohitkhare",
  linkedin: "https://www.linkedin.com/in/themohitkhare",
  notes: "https://notes.sastaspace.com",
  email: "mailto:hi@sastaspace.com",
};

export function Footer() {
  return (
    <footer className={styles.foot}>
      <div className={styles.footRow}>
        <div className={styles.footSig}>
          Built <strong>sasta</strong>. Shared openly.
          <br />© Mohit Khare, 2026.
        </div>
        <div className={styles.footLinks}>
          <a href={SOCIAL.github}>github</a>
          <a href={SOCIAL.linkedin}>linkedin</a>
          <a href={SOCIAL.notes}>notes</a>
          <a href={SOCIAL.email}>email</a>
        </div>
      </div>
    </footer>
  );
}
