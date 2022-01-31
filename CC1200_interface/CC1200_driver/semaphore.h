#include <mutex>
#include <condition_variable>
using namespace std;

class Semaphore
{
public:

  Semaphore(int count_ = 0) : count{count_}
  {}

  void p() { wait(); }
  void v() { notify(); }

  void notify();
  void wait();

private:

  mutex mtx;
  condition_variable cv;
  int count;
};