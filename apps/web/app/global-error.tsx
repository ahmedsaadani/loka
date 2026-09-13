"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="fr">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          padding: "3rem 1rem",
          textAlign: "center",
          color: "#26272b",
        }}
      >
        <h1>Un problème est survenu</h1>
        <p>{error.digest ? `Référence : ${error.digest}` : "Réessayez dans quelques instants."}</p>
        <button
          onClick={reset}
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1.25rem",
            background: "#b8552e",
            color: "#fff",
            border: 0,
            borderRadius: 8,
          }}
        >
          Réessayer
        </button>
      </body>
    </html>
  );
}
