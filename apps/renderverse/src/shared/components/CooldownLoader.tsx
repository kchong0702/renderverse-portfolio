import styles from "./CooldownLoader.module.css";

export default function CooldownLoader() {
  return (
    <div className={styles.loadercontainer}>
      <div className={styles.loader}></div>
    </div>
  );
}
