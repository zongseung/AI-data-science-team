import { OfficeCanvas } from "./canvas/OfficeCanvas";

export default function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#05050a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <OfficeCanvas />
    </div>
  );
}
