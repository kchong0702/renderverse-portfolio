import styles from "./Searchbar.module.css";
import { IoMdArrowBack, IoMdArrowForward, IoMdRefresh } from "react-icons/io";
import { HiDotsVertical } from "react-icons/hi";

export default function Searchbar() {
  return (
    <div className={styles.searchbarcontent}>
      <IoMdArrowBack size={20} className={styles.searchbarassets} />
      <IoMdArrowForward size={20} className={styles.searchbarassets} />
      <IoMdRefresh size={20} className={styles.searchbarassets} />
      <div className={styles.searchbar}>
        <span>{window.location.host + "/projects"}</span>
      </div>
      <HiDotsVertical size={20} className={styles.menuicon} />
    </div>
  );
}
