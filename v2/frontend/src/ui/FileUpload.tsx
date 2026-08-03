import { useId, useRef, type ChangeEvent, type InputHTMLAttributes } from "react";
import { Button } from "./Button";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & {
  label?: string;
  fileName?: string | null;
  onFileChange: (file: File | null) => void;
  "data-testid"?: string;
};

/**
 * Upload customizado: input file visualmente oculto; botão DS + nome do arquivo.
 * Preserva `setInputFiles` via input real com data-testid.
 */
export function FileUpload({
  label = "Anexar arquivo",
  fileName,
  onFileChange,
  disabled,
  accept,
  className,
  "data-testid": testId = "file-upload",
  id,
  ...rest
}: Props) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    onFileChange(file);
  }

  return (
    <div className={["file-upload", className].filter(Boolean).join(" ")} data-testid={`${testId}-wrap`}>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="file-upload-input"
        accept={accept}
        disabled={disabled}
        onChange={handleChange}
        data-testid={testId}
        {...rest}
      />
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        {label}
      </Button>
      <span className="file-upload-name" data-testid={`${testId}-name`}>
        {fileName?.trim() || "Nenhum arquivo selecionado"}
      </span>
    </div>
  );
}
