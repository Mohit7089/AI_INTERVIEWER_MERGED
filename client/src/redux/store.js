// import {configureStore} from '@reduxjs/toolkit'
// import userSlice from "./userSlice.js"

// export default configureStore({
//     reducer:{
//         user:userSlice
//     },
// })

import { configureStore } from '@reduxjs/toolkit'
import userSlice from "./userSlice"
export default configureStore({
  reducer: {
    user:userSlice

  },
})