import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      "test/**", // testing-library asserts make eslint-plugin-jest-dom suggestions noisy
    ],
  },
  {
    rules: {
      // Brand: discourage `console.log` left in code, but warn (not error)
      "no-console": ["warn", { allow: ["warn", "error"] }],
      // The brand voice uses apostrophes liberally in JSX text. Escaping them
      // adds visual noise without improving HTML safety. JSX renders them fine.
      "react/no-unescaped-entities": "off",
    },
  },
];

export default config;
