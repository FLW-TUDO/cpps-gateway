#include "semaphore.h"

void Semaphore::notify() {
    unique_lock<mutex> lck(mtx);
    ++count;
    cv.notify_one();
  }

void Semaphore::wait() {
    unique_lock<mutex> lck(mtx);
    while(count == 0)
    {
      cv.wait(lck);
    }

    --count;
}