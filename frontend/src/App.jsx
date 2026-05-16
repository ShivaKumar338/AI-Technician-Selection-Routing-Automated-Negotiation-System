import { RouterProvider } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { router } from "./router";

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1E293B",
            color: "#F1F5F9",
            border: "1px solid #334155",
          },
        }}
      />
    </>
  );
}
