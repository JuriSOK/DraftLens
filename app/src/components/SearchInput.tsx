import styles from "./SearchInput.module.css";

export function SearchInput({
  value,
  onChange,
  placeholder = "Search prospects…",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className={styles.wrap}>
      <label htmlFor="prospect-search" className="visually-hidden">
        Search prospects by name
      </label>
      <input
        id="prospect-search"
        type="search"
        className={styles.input}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
